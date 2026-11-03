"""Isolated experiment: SQLite writer coordination, not a production lock."""
import asyncio
import json
from uuid import uuid4

from sqlalchemy import event, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.knowledge import KnowledgeEntry
from app.models.knowledge_workspace import KnowledgeRevision, KnowledgeState
from app.services.knowledge.workspace import KnowledgeWorkspaceService
from app.tests.async_db import open_test_session


def test_sqlite_state_noop_update_blocks_withdraw_until_transaction_release(tmp_path):
    async def scenario():
        engine, seed = await open_test_session(str(tmp_path / 'state-lock.db'))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        entered_update = asyncio.Event()

        @event.listens_for(engine.sync_engine, 'before_cursor_execute')
        def observe(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith('UPDATE KNOWLEDGE_ENTRIES'):
                entered_update.set()

        entry = KnowledgeEntry(title='景点', category='景点信息', content='资料', source='来源',
                               aliases='', metadata_json=json.dumps({'attraction_id': 'A'}))
        seed.add_all([entry, KnowledgeState(id=1, epoch=1)])
        await seed.flush()
        revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title,
                                     category=entry.category, content=entry.content, source=entry.source,
                                     aliases='', metadata_json=entry.metadata_json)
        seed.add(revision)
        await seed.flush()
        entry.published_revision_id = revision.id
        entry_id = entry.id
        await seed.commit()
        try:
            async with sessions() as holder, sessions() as writer:
                result = await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1)
                                              .values(epoch=KnowledgeState.epoch))
                assert result.rowcount == 1
                pending = asyncio.create_task(KnowledgeWorkspaceService(writer).withdraw(entry_id))
                try:
                    await asyncio.wait_for(entered_update.wait(), timeout=2)
                    try:
                        await asyncio.wait_for(asyncio.shield(pending), timeout=0.1)
                        raise AssertionError('withdraw completed while holder transaction was open')
                    except TimeoutError:
                        pass
                    current = await holder.scalar(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
                    assert current.withdrawn_at is None
                    await holder.commit()
                    await asyncio.wait_for(pending, timeout=3)
                finally:
                    if not pending.done():
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
                async with sessions() as verify:
                    persisted = await verify.get(KnowledgeEntry, entry_id)
                    assert persisted.withdrawn_at is not None
                    assert (await verify.get(KnowledgeState, 1)).epoch == 2
        finally:
            await seed.close()
            await engine.dispose()

    asyncio.run(scenario())
