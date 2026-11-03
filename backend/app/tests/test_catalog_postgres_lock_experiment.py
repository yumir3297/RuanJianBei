"""Opt-in experiment against a migrated, disposable local PostgreSQL database."""
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
from app.services.knowledge.workspace import KnowledgeWorkspaceService


@pytest.mark.skipif(not os.getenv("GUIDE_TEST_POSTGRES_URL"), reason="requires disposable PostgreSQL")
def test_postgres_state_lock_orders_real_withdraw():
    url = make_url(os.environ["GUIDE_TEST_POSTGRES_URL"])
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("guide_test_")
    assert not url.host and url.query.get("host", "").startswith("/private/tmp/")

    async def scenario():
        engine = create_async_engine(url)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as seed:
                assert await seed.get(KnowledgeState, 1) is not None
                entry = KnowledgeEntry(title="锁实验", category="景点信息", content="资料", source="测试",
                                       aliases="", metadata_json=json.dumps({"attraction_id": str(uuid4())}))
                seed.add(entry); await seed.flush()
                revision = KnowledgeRevision(id=str(uuid4()), knowledge_entry_id=entry.id, title=entry.title,
                    category=entry.category, content=entry.content, source=entry.source, aliases="", metadata_json=entry.metadata_json)
                seed.add(revision); await seed.flush(); entry.published_revision_id = revision.id
                entry_id = entry.id
                await seed.commit()
            async with sessions() as holder, sessions() as writer:
                result = await holder.execute(update(KnowledgeState).where(KnowledgeState.id == 1).values(epoch=KnowledgeState.epoch))
                assert result.rowcount == 1
                pid = await writer.scalar(text("SELECT pg_backend_pid()"))
                task = asyncio.create_task(KnowledgeWorkspaceService(writer).withdraw(entry_id))
                try:
                    blocked = False
                    for _ in range(200):
                        if task.done():
                            raise AssertionError("withdraw completed before lock release")
                        async with sessions() as observer:
                            wait_type = await observer.scalar(text(
                                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid})
                        if wait_type == "Lock":
                            blocked = True
                            break
                        await asyncio.sleep(.01)
                    assert blocked, "writer did not reach a lock wait"
                    await holder.commit()
                    await asyncio.wait_for(task, timeout=5)
                finally:
                    if not task.done():
                        task.cancel(); await asyncio.gather(task, return_exceptions=True)
            async with sessions() as verify:
                assert (await verify.get(KnowledgeEntry, entry_id)).withdrawn_at is not None
        finally:
            await engine.dispose()
    asyncio.run(scenario())
