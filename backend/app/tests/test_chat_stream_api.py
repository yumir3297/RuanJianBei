from __future__ import annotations

import asyncio
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.services.qa.stream_events import StreamEvent
from app.services.capacity import CapacityLimiter


class _FakePipeline:
    async def stream_chat(self, _payload):
        yield StreamEvent(type="text", data={"text": "测试回答", "is_complete": True})
        yield StreamEvent(type="done", data={"chat_log_id": 1})


class _FakeSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def _build_client(monkeypatch, *, fail_build: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(chat_api.router, prefix="/api/chat")

    async def override_session():
        return _FakeSession()

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


def test_tourist_stream_rejects_guide_loop_context(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    client.app.dependency_overrides[get_app_settings] = lambda: Settings(
        app_env="development", guide_loop_pilot_enabled=True, llm_provider="stub", tts_provider="stub"
    )
    response = client.post(
        "/api/chat/stream",
        json={"query": "测试问题", "session_id": "pilot", "text_only": True,
              "guide_loop": {"poi_id": "bathing"}},
    )
    assert response.status_code == 403
    assert "event: text" not in response.text


def test_stream_converts_pipeline_failure_to_sse_error(monkeypatch) -> None:
    response = _build_client(monkeypatch, fail_build=True).post(
        "/api/chat/stream",
        json={"query": "介绍灵山", "session_id": "stream-error", "text_only": True},
    )

    assert response.status_code == 200
    assert "event: status" in response.text
    assert "event: error" in response.text
    assert "导览服务处理回答时发生错误" in response.text


def test_stream_does_not_print_private_user_question(monkeypatch, capsys) -> None:
    response = _build_client(monkeypatch).post(
        "/api/chat/stream", json={"query": "私密问题甲乙", "session_id": "private-session", "text_only": True}
    )
    assert response.status_code == 200
    assert "私密问题甲乙" not in capsys.readouterr().out


def test_heartbeat_keeps_stream_open_without_cancelling_slow_generator() -> None:
    async def run():
        async def slow():
            yield b"first\n\n"
            await asyncio.sleep(0.04)
            yield b"last\n\n"

        return [chunk async for chunk in chat_api.with_sse_heartbeat(slow(), interval=0.01)]

    chunks = asyncio.run(run())
    assert chunks[0] == b"first\n\n"
    assert chunks[-1] == b"last\n\n"
    assert any(chunk.startswith(b":") for chunk in chunks[1:-1])


def test_heartbeat_closes_pending_producer_on_client_stop() -> None:
    async def run():
        cancelled = asyncio.Event()

        async def producer():
            try:
                yield b"first\n\n"
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        stream = chat_api.with_sse_heartbeat(producer(), interval=0.01)
        assert await anext(stream) == b"first\n\n"
        assert (await anext(stream)).startswith(b":")
        await stream.aclose()
        assert cancelled.is_set()

    asyncio.run(run())


def test_heartbeat_keeps_source_generator_in_one_context_across_yields() -> None:
    async def run():
        request_state = ContextVar("heartbeat_request_state", default=None)

        async def source():
            token = request_state.set("active-request")
            try:
                yield b"first\n\n"
                await asyncio.sleep(0.02)
                assert request_state.get() == "active-request"
                yield b"last\n\n"
            finally:
                request_state.reset(token)

        return [chunk async for chunk in chat_api.with_sse_heartbeat(source(), interval=0.005)]

    chunks = asyncio.run(run())
    assert chunks[0] == b"first\n\n"
    assert chunks[-1] == b"last\n\n"


def test_chat_rejects_over_capacity_before_starting_stream(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    limiter = CapacityLimiter({"chat": 1})
    lease = limiter.try_acquire("chat")
    client.app.state.guide_capacity = limiter
    try:
        response = client.post("/api/chat/stream", json={"query": "问题", "session_id": "s"})
        assert response.status_code == 429
        assert "服务繁忙" in response.json()["detail"]
    finally:
        lease.release()


def test_chat_capacity_is_released_after_success_and_failure(monkeypatch) -> None:
    client = _build_client(monkeypatch, fail_build=True)
    client.app.state.guide_capacity = CapacityLimiter({"chat": 1})
    payload = {"query": "问题", "session_id": "s"}
    first = client.post("/api/chat/stream", json=payload)
    second = client.post("/api/chat/stream", json=payload)
    assert first.status_code == second.status_code == 200
    assert "event: error" in first.text


def test_chat_capacity_released_when_client_closes_stream() -> None:
    async def scenario():
        app = FastAPI()
        limiter = CapacityLimiter({"chat": 1})
        app.state.guide_capacity = limiter
        request = Request({"type": "http", "app": app, "headers": []})
        session = _FakeSession()
        response = await chat_api.stream_chat(
            chat_api.ChatRequest(query="问题", session_id="s"), request, session, Settings(),
        )
        assert limiter.try_acquire("chat") is None
        await anext(response.body_iterator)
        await response.body_iterator.aclose()
        assert session.closed
        lease = limiter.try_acquire("chat")
        assert lease is not None
        lease.release()
    asyncio.run(scenario())
