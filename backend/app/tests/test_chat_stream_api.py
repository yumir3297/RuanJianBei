from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.services.qa.stream_events import StreamEvent


class _FakePipeline:
    async def stream_chat(self, _payload):
        yield StreamEvent(type="text", data={"text": "测试回答", "is_complete": True})
        yield StreamEvent(type="done", data={"chat_log_id": 1})


def _build_client(monkeypatch, *, fail_build: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(chat_api.router, prefix="/api/chat")

    async def override_session():
        return object()

    def override_settings() -> Settings:
        return Settings(llm_provider="stub", tts_provider="stub")

    async def fake_build_pipeline(*_args, **_kwargs):
        if fail_build:
            raise RuntimeError("build failed")
        return _FakePipeline()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_app_settings] = override_settings
    monkeypatch.setattr(chat_api, "build_pipeline", fake_build_pipeline)
    return TestClient(app)


def test_stream_sends_status_before_answer(monkeypatch) -> None:
    response = _build_client(monkeypatch).post(
        "/api/chat/stream",
        json={"query": "介绍灵山", "session_id": "stream-order", "text_only": True},
    )

    assert response.status_code == 200
    body = response.text
    assert body.index("event: status") < body.index("event: text") < body.index("event: done")
    assert "正在准备导览知识" in body


def test_stream_converts_pipeline_failure_to_sse_error(monkeypatch) -> None:
    response = _build_client(monkeypatch, fail_build=True).post(
        "/api/chat/stream",
        json={"query": "介绍灵山", "session_id": "stream-error", "text_only": True},
    )

    assert response.status_code == 200
    assert "event: status" in response.text
    assert "event: error" in response.text
    assert "导览服务处理回答时发生错误" in response.text
