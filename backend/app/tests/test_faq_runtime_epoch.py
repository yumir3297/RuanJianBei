import asyncio
import select
import sqlite3
import subprocess
import sys
import pytest

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.faq import FAQEntryRecord
from app.models.knowledge_workspace import KnowledgeState
from app.services.qa import runtime
from app.services.qa.faq_matcher import FAQMatcher
from app.services.qa.faq_matcher import FAQEntry
from app.tests.async_db import open_test_session


def test_empty_faq_does_not_reload_repeatedly(monkeypatch, tmp_path):
    old_reload = FAQMatcher.reload
    calls = 0

    async def counted(self, session):
        nonlocal calls
        calls += 1
        return await old_reload(self, session)

    monkeypatch.setattr(runtime, "_faq_matcher", FAQMatcher())
    monkeypatch.setattr(FAQMatcher, "reload", counted)

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "empty.db"))
        try:
            await runtime.get_runtime_faq_matcher(session)
            await runtime.get_runtime_faq_matcher(session)
            assert calls == 1
        finally:
            await session.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_concurrent_requests_share_one_refresh(monkeypatch):
    class Visibility:
        def __init__(self, _session): pass
        async def read_epoch(self): return 2

    old = FAQMatcher()
    old.add([FAQEntry(id="old", category="test", aliases=["问题"], answer="旧", sources=[])])
    old.knowledge_epoch = 1
    monkeypatch.setattr(runtime, "_faq_matcher", old)
    monkeypatch.setattr(runtime, "VisibilityService", Visibility)

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def load(matcher, _session):
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            matcher.add([FAQEntry(id="new", category="test", aliases=["问题"], answer="新", sources=[])])

        monkeypatch.setattr(FAQMatcher, "load_from_db", load)
        tasks = [asyncio.create_task(runtime.get_runtime_faq_matcher(object())) for _ in range(3)]
        await started.wait()
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(*tasks)
        assert all(m.match_exact("问题").answer == "新" for m in results)
        assert calls == 1

    asyncio.run(scenario())


def test_reload_keeps_old_matcher_usable_until_new_matcher_is_ready(monkeypatch):
    old = FAQMatcher()
    old.add([FAQEntry(id="old", category="test", aliases=["问题"], answer="旧答案", sources=[])])
    monkeypatch.setattr(runtime, "_faq_matcher", old)

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed_load(matcher, _session):
            started.set()
            await release.wait()
            matcher.add([FAQEntry(id="new", category="test", aliases=["问题"], answer="新答案", sources=[])])

        monkeypatch.setattr(FAQMatcher, "load_from_db", delayed_load)
        task = asyncio.create_task(runtime.reload_runtime_faq_matcher(None))
        await started.wait()
        try:
            assert old.match_exact("问题").answer == "旧答案"
        finally:
            release.set()
            await task
        assert runtime._faq_matcher.match_exact("问题").answer == "新答案"
        assert runtime._faq_matcher is not old

    asyncio.run(scenario())


@pytest.mark.skipif(sys.platform == "win32", reason="select on subprocess pipes is not supported on Windows")
def test_faq_worker_refreshes_after_another_process_updates_database(tmp_path):
    database = tmp_path / "cross-process.db"

    async def setup():
        engine, session = await open_test_session(str(database))
        session.add_all([KnowledgeState(id=1, epoch=1), FAQEntryRecord(
            id="f", category="test", aliases_json='["问题"]', answer="旧答案", sources_json="[]")])
        await session.commit()
        await session.close()
        await engine.dispose()

    asyncio.run(setup())
    script = '''
import asyncio, sys
from app.services.qa.runtime import get_runtime_faq_matcher
from app.tests.async_db import open_test_session
async def main():
    engine, session = await open_test_session(sys.argv[1])
    try:
        matcher = await get_runtime_faq_matcher(session)
        print(matcher.match_exact("问题").answer, flush=True)
        await asyncio.to_thread(sys.stdin.readline)
        matcher = await get_runtime_faq_matcher(session)
        print(matcher.match_exact("问题").answer, flush=True)
    finally:
        await session.close()
        await engine.dispose()
asyncio.run(main())
'''
    child = subprocess.Popen([sys.executable, "-u", "-c", script, str(database)], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([child.stdout], [], [], 15)[0], "worker did not load FAQ"
        assert child.stdout.readline().strip() == "旧答案"
        with sqlite3.connect(database) as conn:
            conn.execute("UPDATE faq_entries SET answer=? WHERE id='f'", ("新答案",))
            conn.execute("UPDATE knowledge_state SET epoch=2 WHERE id=1")
        output, errors = child.communicate("continue\n", timeout=15)
        assert child.returncode == 0, errors
        assert output.strip() == "新答案"
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()


def test_reload_detects_epoch_change_and_recovers(monkeypatch):
    class Visibility:
        values = iter([1, 2, 2, 2])

        def __init__(self, _session):
            pass

        async def read_epoch(self):
            return next(self.values)

    class Matcher:
        semantic_index = None
        knowledge_epoch = None

        async def reload(self, _session):
            return 1.0

    matcher = Matcher()
    monkeypatch.setattr(runtime, "_faq_matcher", matcher)
    monkeypatch.setattr(runtime, "FAQMatcher", Matcher)
    monkeypatch.setattr(runtime, "VisibilityService", Visibility)
    monkeypatch.setattr(runtime, "_faq_reload_failed", False)

    async def scenario():
        with pytest.raises(RuntimeError, match="version changed"):
            await runtime.reload_runtime_faq_matcher(object())
        assert runtime.faq_reload_failed()
        assert matcher.knowledge_epoch != 2
        await runtime.reload_runtime_faq_matcher(object())
        assert not runtime.faq_reload_failed()
        assert runtime._faq_matcher.knowledge_epoch == 2
        assert matcher.knowledge_epoch is None

    asyncio.run(scenario())


def test_runtime_reloads_after_other_session_updates_faq_and_epoch(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "_faq_matcher", FAQMatcher())

    async def scenario():
        engine, session = await open_test_session(str(tmp_path / "faq.db"))
        try:
            session.add_all([
                KnowledgeState(id=1, epoch=1),
                FAQEntryRecord(id="f", category="test", aliases_json='["问题"]', answer="旧答案", sources_json="[]"),
            ])
            await session.commit()
            matcher = await runtime.get_runtime_faq_matcher(session)
            assert matcher.match_exact("问题").answer == "旧答案"
            async with async_sessionmaker(engine, expire_on_commit=False)() as writer:
                (await writer.get(FAQEntryRecord, "f")).answer = "新答案"
                (await writer.get(KnowledgeState, 1)).epoch = 2
                await writer.commit()
            matcher = await runtime.get_runtime_faq_matcher(session)
            assert matcher.match_exact("问题").answer == "新答案"
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())
