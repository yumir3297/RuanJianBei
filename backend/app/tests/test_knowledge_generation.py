from __future__ import annotations

import asyncio

from app.api import chat
from app.core.config import get_settings
from app.repositories.knowledge_generation import KnowledgeGenerationRepository
from app.services.rag.retriever import RepositoryBackedRAGService
from app.tests.async_db import open_test_session


def test_knowledge_generation_is_durable_and_index_generation_lags_after_change(tmp_path) -> None:
    async def scenario():
        db_path = str(tmp_path / "generation.db")
        engine, session = await open_test_session(db_path)
        try:
            repository = KnowledgeGenerationRepository(session)
            initial = await repository.get()
            initial_generation = initial.generation
            await repository.mark_indexed(initial.generation)
            await session.commit()

            await repository.bump()
            await session.commit()
        finally:
            await session.close()
            await engine.dispose()

        engine, session = await open_test_session(db_path)
        try:
            current = await KnowledgeGenerationRepository(session).get()
            assert current.generation == initial_generation + 1
            assert current.indexed_generation == initial_generation
        finally:
            await session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_qa_pipeline_uses_live_database_fallback_when_vector_index_is_stale(monkeypatch) -> None:
    async def scenario():
        engine, session = await open_test_session()
        try:
            monkeypatch.setattr(chat, "get_runtime_faq_matcher", lambda *_args, **_kwargs: _resolved(None))
            monkeypatch.setattr(chat, "get_cached_embedder", lambda *_args, **_kwargs: object())
            monkeypatch.setattr(chat, "get_cached_llm_service", lambda *_args, **_kwargs: object())
            monkeypatch.setattr(
                chat,
                "get_cached_vector_store",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("stale index must not be opened")),
            )

            pipeline = await chat.build_pipeline(session, get_settings())
            assert isinstance(pipeline.rag_service, RepositoryBackedRAGService)
            first_namespace = pipeline.answer_cache_namespace
            await KnowledgeGenerationRepository(session).bump()
            await session.commit()
            next_pipeline = await chat.build_pipeline(session, get_settings())
            assert next_pipeline.answer_cache_namespace != first_namespace
        finally:
            await session.close()
            await engine.dispose()

    async def _resolved(value):
        return value

    asyncio.run(scenario())
