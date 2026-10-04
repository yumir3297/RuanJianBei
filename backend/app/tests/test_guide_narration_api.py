from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import guide as guide_api
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.services.qa.stream_events import StreamEvent
from app.services.tts.base import TTSAudio


class _FakeTTS:
    async def synthesize(self, _text: str) -> TTSAudio:
        return TTSAudio(base64_audio="QUJD", duration_ms=1234, provider="fake")


class _FakePipeline:
    def __init__(self, *, text: str = "灵山大佛高88米，是灵山胜境的标志性景观。"):
        self._text = text
        self.tts_service = _FakeTTS()

    async def stream_chat(self, _payload):
        yield StreamEvent(type="status", data={"text": "..."})
        yield StreamEvent(type="text", data={"text": self._text, "is_complete": True})


def _build_client(monkeypatch, *, pipeline=None, fail_build: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(guide_api.router, prefix="/api/guide")

    async def override_session():
        return object()

    def override_settings() -> Settings:
        return Settings(llm_provider="stub", tts_provider="stub")

    async def fake_build_pipeline(*_args, **_kwargs):
        if fail_build:
            raise RuntimeError("build failed")
        return pipeline if pipeline is not None else _FakePipeline()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_app_settings] = override_settings
    monkeypatch.setattr(guide_api, "build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(guide_api, "_NARRATION_CACHE", {})
    return TestClient(app)


def test_clean_strips_styler_prefix_and_evidence_markers() -> None:
    raw = "好的，让我为您道来—— 灵山大佛高88米[证据1]，是灵山胜境的地标。[2]"
    cleaned = guide_api._clean(raw)
    assert cleaned.startswith("灵山大佛高88米")
    assert "[证据1]" not in cleaned
    assert "[2]" not in cleaned
    assert "好的，让我为您道来" not in cleaned


def test_clean_strips_various_styler_prefixes() -> None:
    for prefix in ("来，咱们看看—— ", "根据官方资料记载—— ", "嗯，这个问题问得好呢—— "):
        cleaned = guide_api._clean(f"{prefix}九龙灌浴位于菩提大道北端。")
        assert cleaned.startswith("九龙灌浴位于菩提大道北端。"), prefix


def test_clean_strips_degraded_lead_line() -> None:
    raw = "AI讲解服务暂时不可用，先为你展示检索到的官方资料：\n[证据1] 灵山大佛高88米"
    cleaned = guide_api._clean(raw)
    assert cleaned.startswith("[证据1]") or cleaned.startswith("灵山大佛高88米")
    assert "AI讲解服务暂时不可用" not in cleaned


def test_clean_keeps_plain_text_untouched() -> None:
    raw = "灵山大佛高88米，是灵山胜境的标志性景观。"
    assert guide_api._clean(raw) == raw


def test_narration_returns_text_and_audio(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["attraction"] == "灵山大佛"
    assert "88米" in body["text"]
    assert body["base64_audio"] == "QUJD"
    assert body["duration_ms"] == 1234
    assert body["available"] is True
    assert body["cached"] is False


def test_narration_second_call_is_cached(monkeypatch) -> None:
    pipeline = _FakePipeline()
    calls = {"n": 0}

    original = pipeline.stream_chat

    async def counting(_payload):
        calls["n"] += 1
        async for event in original(_payload):
            yield event

    pipeline.stream_chat = counting
    client = _build_client(monkeypatch, pipeline=pipeline)
    client.post("/api/guide/narration", json={"attraction": "灵山大佛"})
    second = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert calls["n"] == 1
    assert second.json()["cached"] is True


def test_narration_degrades_without_5xx_on_pipeline_failure(monkeypatch) -> None:
    client = _build_client(monkeypatch, fail_build=True)
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "pipeline_unavailable"
    assert body["text"] == ""


def test_narration_degrades_when_llm_returns_empty(monkeypatch) -> None:
    client = _build_client(monkeypatch, pipeline=_FakePipeline(text=""))
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "llm_unavailable"
