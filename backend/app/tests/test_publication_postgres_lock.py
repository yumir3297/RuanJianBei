"""Opt-in lock experiment; requires an isolated disposable local PostgreSQL database."""
import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.services.knowledge.publication import KnowledgePublicationService
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.tests.test_knowledge_publication import FakeEmbedder, FakeVectorStore


@pytest.mark.skipif(not os.getenv('GUIDE_TEST_POSTGRES_URL'), reason='requires disposable PostgreSQL')
def test_postgres_withdraw_waits_for_knowledge_state_lock():
    url = make_url(os.environ['GUIDE_TEST_POSTGRES_URL'])
    assert url.drivername == 'postgresql+asyncpg'
    assert (url.database or '').startswith('guide_test_')
    assert not url.host and url.query.get('host', '').startswith('/private/tmp/')

    async def run():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as seed:
                entry = KnowledgeEntry(title='撤回锁测试', category='景点信息', content='合成', source='测试')
                seed.add(entry)
                await seed.commit()
                entry_id = entry.id
            async with sessions() as holder, sessions() as writer:
                await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch))
                task = asyncio.create_task(KnowledgeWorkspaceService(writer).withdraw(entry_id))
                try:
                    blocked = False
                    for _ in range(200):
                        if task.done():
                            break
                        async with sessions() as observer:
                            count = await observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%knowledge_state%'"))
                        if count:
                            blocked = True
                            break
                        await asyncio.sleep(.01)
                    assert blocked, 'withdrawal did not wait for knowledge state lock'
                    async with sessions() as observer:
                        observed = await observer.get(KnowledgeEntry, entry_id)
                        assert observed.withdrawn_at is None
                    await holder.commit()
                    await asyncio.wait_for(task, 5)
                    async with sessions() as observer:
                        assert (await observer.get(KnowledgeEntry, entry_id)).withdrawn_at is not None
                finally:
                    if not task.done():
                        await holder.rollback()
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        finally:
            await engine.dispose()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('GUIDE_TEST_POSTGRES_URL'), reason='requires disposable PostgreSQL')
def test_postgres_concurrent_duplicate_codes_publish_only_one():
    url = make_url(os.environ['GUIDE_TEST_POSTGRES_URL'])
    assert url.drivername == 'postgresql+asyncpg'
    assert (url.database or '').startswith('guide_test_')
    assert not url.host and url.query.get('host', '').startswith('/private/tmp/')

    async def run():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        code = str(uuid4())
        jobs = []
        try:
            async with sessions() as seed:
                for title in ('甲', '乙'):
                    metadata = json.dumps({'attraction_id': code})
                    entry = KnowledgeEntry(title=title, category='景点信息', content='合成', source='测试')
                    seed.add(entry)
                    await seed.flush()
                    revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=title,
                                                 category='景点信息', content='合成', source='测试', metadata_json=metadata)
                    seed.add(revision)
                    await seed.flush()
                    entry.draft_revision_id = revision.id
                    jobs.append((entry.id, revision.id))
                await seed.commit()
            job_ids = []
            for entry_id, revision_id in jobs:
                async with sessions() as db:
                    service = KnowledgePublicationService(db, FakeEmbedder(), FakeVectorStore())
                    job = await service.create_publication([{'entry_id': entry_id, 'revision_id': revision_id,
                                                             'expected_version': 1}], idempotency_key=str(uuid4()))
                    job_ids.append(job.id)
            async def publish(job_id):
                async with sessions() as db:
                    service = KnowledgePublicationService(db, FakeEmbedder(), FakeVectorStore())
                    await service.run_publication(job_id)
                    return (await service.get_publication(job_id)).state
            states = await asyncio.wait_for(asyncio.gather(*(publish(job_id) for job_id in job_ids)), 20)
            assert sorted(states) == ['failed', 'succeeded']
            async with sessions() as db:
                entries = [await db.get(KnowledgeEntry, entry_id) for entry_id, _ in jobs]
                assert sum(entry.published_revision_id is not None for entry in entries) == 1
                assert sum(entry.draft_revision_id is not None for entry in entries) == 1
        finally:
            await engine.dispose()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('GUIDE_TEST_POSTGRES_URL'), reason='requires disposable PostgreSQL')
def test_postgres_publication_waits_for_state_lock(monkeypatch):
    url = make_url(os.environ['GUIDE_TEST_POSTGRES_URL'])
    assert url.drivername == 'postgresql+asyncpg'
    assert (url.database or '').startswith('guide_test_')
    assert not url.host and url.query.get('host', '').startswith('/private/tmp/')

    async def run():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ready, release = asyncio.Event(), asyncio.Event()
        try:
            async with sessions() as seed:
                assert await seed.get(KnowledgeState, 1) is not None
                entry = KnowledgeEntry(title='测试景点', category='景点信息', content='新资料', source='测试')
                seed.add(entry); await seed.flush()
                revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title,
                    category=entry.category, content=entry.content, source=entry.source)
                seed.add(revision); await seed.flush(); entry.draft_revision_id = revision.id
                entry_id, revision_id = entry.id, revision.id
                await seed.commit()
            async with sessions() as publisher, sessions() as holder:
                service = KnowledgePublicationService(publisher, FakeEmbedder(), FakeVectorStore())
                job = await service.create_publication([{'entry_id': entry_id, 'revision_id': revision_id,
                                                         'expected_version': 1}], idempotency_key=str(uuid4()))
                original = service._commit_publication
                async def gated(*args):
                    ready.set()
                    await asyncio.wait_for(release.wait(), 5)
                    return await original(*args)
                monkeypatch.setattr(service, '_commit_publication', gated)
                task = asyncio.create_task(service.run_publication(job.id))
                try:
                    await asyncio.wait_for(ready.wait(), 5)
                    result = await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1)
                                                  .values(epoch=KnowledgeState.epoch))
                    assert result.rowcount == 1
                    release.set()
                    blocked = False
                    for _ in range(200):
                        if task.done():
                            break
                        async with sessions() as observer:
                            count = await observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%knowledge_state%'"))
                        if count:
                            blocked = True
                            break
                        await asyncio.sleep(.01)
                    assert blocked, 'publication did not reach a state lock wait'
                    await holder.commit()
                    await asyncio.wait_for(task, 5)
                    assert (await service.get_publication(job.id)).state == 'succeeded'
                finally:
                    release.set()
                    if not task.done():
                        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        finally:
            await engine.dispose()
    asyncio.run(run())
