import asyncio
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.models.knowledge_workspace import KnowledgeState
from app.services.knowledge.publication import KnowledgePublicationService
from app.tests.async_db import open_test_session
from app.tests.test_knowledge_publication import FakeEmbedder, FakeVectorStore, _seed_drafts


def test_publication_waits_for_confirmation_state_lock(tmp_path, monkeypatch):
    path = str(tmp_path / 'publication-lock.db')
    selected = _seed_drafts(path)

    async def scenario():
        engine, seed = await open_test_session(path)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ready, release, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()
        @event.listens_for(engine.sync_engine, 'before_cursor_execute')
        def observe(_conn, _cursor, statement, _params, _context, _many):
            if statement.lstrip().upper().startswith('UPDATE KNOWLEDGE_ENTRIES'):
                attempted.set()
        try:
            async with sessions() as publisher, sessions() as holder:
                service = KnowledgePublicationService(publisher, FakeEmbedder(), FakeVectorStore())
                job = await service.create_publication([{'entry_id': i, 'revision_id': r, 'expected_version': 1} for i, r in selected], idempotency_key='publication')
                original = service._commit_publication
                async def gated(*args):
                    ready.set()
                    await asyncio.wait_for(release.wait(), 3)
                    return await original(*args)
                monkeypatch.setattr(service, '_commit_publication', gated)
                task = asyncio.create_task(service.run_publication(job.id))
                try:
                    await asyncio.wait_for(ready.wait(), 3)
                    await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch))
                    release.set()
                    await asyncio.wait_for(attempted.wait(), 3)
                    try:
                        await asyncio.wait_for(asyncio.shield(task), .1)
                        raise AssertionError('publication finished while state lock held')
                    except TimeoutError:
                        pass
                    await holder.commit()
                    await asyncio.wait_for(task, 3)
                    assert (await service.get_publication(job.id)).state == 'succeeded'
                finally:
                    release.set()
                    if not task.done():
                        task.cancel(); await asyncio.gather(task, return_exceptions=True)
        finally:
            await seed.close(); await engine.dispose()
    asyncio.run(scenario())
