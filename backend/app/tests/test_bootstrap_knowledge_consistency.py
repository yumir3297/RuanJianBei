from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import bootstrap
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.knowledge_generation import KnowledgeGenerationRepository
from app.tests.async_db import open_test_session


def test_sample_bootstrap_updates_chunks_and_knowledge_generation(tmp_path, monkeypatch) -> None:
    async def scenario():
        db_path = str(tmp_path / "bootstrap.db")
        engine, _session = await open_test_session(db_path)
        monkeypatch.setattr(bootstrap, "AsyncSessionLocal", async_sessionmaker(engine, expire_on_commit=False))
        monkeypatch.setattr(
            bootstrap,
            "get_settings",
            lambda: SimpleNamespace(
                enable_sample_data=True,
                processed_data_available=False,
                default_knowledge_source="sample",
            ),
        )
        try:
            await bootstrap.bootstrap_sample_data()
            assert await KnowledgeRepository(_session).count() == 2
            assert await KnowledgeChunkRepository(_session).count() == 2
            state = await KnowledgeGenerationRepository(_session).get()
            assert state.generation == 2
            assert state.indexed_generation == 0
        finally:
            await _session.close()
            await engine.dispose()

    asyncio.run(scenario())
