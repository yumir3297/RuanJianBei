from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.core.deps import get_db_session
from app.tests.async_db import open_test_session


def _client(db_path):
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/chat")

    async def override_db_session():
        engine, session = await open_test_session(str(db_path))
        try:
            yield session
        finally:
            await session.close()
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(app)
    return client


def test_clear_visitor_memory_endpoint_is_reachable(tmp_path):
    client = _client(tmp_path / "visitor-memory.db")
    response = client.delete("/api/chat/visitor-memory/unknown-visitor-xyz")
    assert response.status_code == 200
    assert response.json()["deleted"] == 0


def test_clear_visitor_memory_rejects_overlong_id(tmp_path):
    client = _client(tmp_path / "visitor-memory-long-id.db")
    response = client.delete("/api/chat/visitor-memory/" + "x" * 200)
    assert response.status_code == 200
    assert response.json()["deleted"] == 0
