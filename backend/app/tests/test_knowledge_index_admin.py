from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin
from app.api.auth import create_admin_token
from app.core.config import get_settings
from app.core.deps import get_db_session
from app.core.exceptions import register_exception_handlers
from app.repositories.knowledge_generation import KnowledgeGenerationRepository
from app.tests.async_db import open_test_session


def _client(tmp_path, monkeypatch, *, fail_build=False, change_knowledge_during_build=False):
    db_path = str(tmp_path / "index-admin.db")
    store_state = {"published": [], "discarded": []}
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(admin.router, prefix="/api/admin")

    async def override_db_session():
        engine, session = await open_test_session(db_path)
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    class Builder:
        def __init__(self, *_args, **_kwargs):
            self.session = _args[0].session

        async def build(self, *, activate=True):
            if fail_build:
                raise RuntimeError("simulated embedding failure")
            if change_knowledge_during_build:
                await KnowledgeGenerationRepository(self.session).bump()
                await self.session.commit()
            return SimpleNamespace(
                total_chunks=1,
                indexed_chunks=1,
                collection_name="test-index",
                embedding_model_name="fake",
                duration_ms=1,
                prepared_generation_name="prepared-index",
            )

    class Store:
        def __init__(self, *_args, **_kwargs):
            pass

        def activate_prepared(self, name):
            store_state["published"].append(name)

        def discard_prepared(self, name):
            store_state["discarded"].append(name)

    monkeypatch.setattr(admin, "RAGIndexBuilder", Builder)
    monkeypatch.setattr(admin, "SentenceTransformerEmbedder", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(admin, "ChromaVectorStore", Store)
    app.dependency_overrides[get_db_session] = override_db_session
    settings = get_settings()
    token = create_admin_token(settings.admin_token_secret)
    return TestClient(app, raise_server_exceptions=False), db_path, {"Authorization": f"Bearer {token}"}, store_state


def test_successful_rebuild_marks_only_the_built_knowledge_generation(tmp_path, monkeypatch) -> None:
    client, db_path, headers, store_state = _client(tmp_path, monkeypatch)

    stale_status = client.get("/api/admin/knowledge-index-status", headers=headers)
    assert stale_status.status_code == 200
    assert stale_status.json()["current"] is False

    response = client.post("/api/admin/build-rag-index", headers=headers)

    assert response.status_code == 200
    assert store_state["published"] == ["prepared-index"]
    current_status = client.get("/api/admin/knowledge-index-status", headers=headers)
    assert current_status.json() == {
        "knowledge_generation": 1,
        "indexed_generation": 1,
        "current": True,
    }
    async def read_state():
        engine, session = await open_test_session(db_path)
        try:
            state = await KnowledgeGenerationRepository(session).get()
            return state.generation, state.indexed_generation
        finally:
            await session.close()
            await engine.dispose()

    assert asyncio.run(read_state()) == (1, 1)


def test_failed_index_build_leaves_index_generation_stale_and_retryable(tmp_path, monkeypatch) -> None:
    client, _db_path, headers, _store_state = _client(tmp_path, monkeypatch, fail_build=True)

    response = client.post("/api/admin/build-rag-index", headers=headers)

    assert response.status_code == 500
    status_response = client.get("/api/admin/knowledge-index-status", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json() == {
        "knowledge_generation": 1,
        "indexed_generation": 0,
        "current": False,
    }


def test_rebuild_refuses_to_mark_a_generation_if_knowledge_changes_during_build(tmp_path, monkeypatch) -> None:
    client, _db_path, headers, _store_state = _client(
        tmp_path,
        monkeypatch,
        change_knowledge_during_build=True,
    )

    response = client.post("/api/admin/build-rag-index", headers=headers)

    assert response.status_code == 409
    status_response = client.get("/api/admin/knowledge-index-status", headers=headers)
    assert status_response.json() == {
        "knowledge_generation": 2,
        "indexed_generation": 0,
        "current": False,
    }


def test_superseded_rebuild_does_not_publish_prepared_vector_generation(tmp_path, monkeypatch) -> None:
    client, _db_path, headers, store_state = _client(
        tmp_path,
        monkeypatch,
        change_knowledge_during_build=True,
    )
    response = client.post("/api/admin/build-rag-index", headers=headers)

    assert response.status_code == 409
    assert store_state["published"] == []
    assert store_state["discarded"] == ["prepared-index"]
