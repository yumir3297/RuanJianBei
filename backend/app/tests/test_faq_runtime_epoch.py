import asyncio
import pytest

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.faq import FAQEntryRecord
from app.models.knowledge_workspace import KnowledgeState
from app.services.qa import runtime
from app.services.qa.faq_matcher import FAQMatcher
from app.tests.async_db import open_test_session


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
    monkeypatch.setattr(runtime, "VisibilityService", Visibility)
    monkeypatch.setattr(runtime, "_faq_reload_failed", False)

    async def scenario():
        with pytest.raises(RuntimeError, match="version changed"):
            await runtime.reload_runtime_faq_matcher(object())
        assert runtime.faq_reload_failed()
        assert matcher.knowledge_epoch != 2
        await runtime.reload_runtime_faq_matcher(object())
        assert not runtime.faq_reload_failed()
        assert matcher.knowledge_epoch == 2

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
