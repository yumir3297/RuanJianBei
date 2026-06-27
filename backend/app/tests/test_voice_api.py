from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.voice import router
from app.core.config import Settings, get_settings


def build_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/asr")
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_transcribe_audio_returns_stub_metadata() -> None:
    client = build_client(Settings(asr_provider="stub"))

    response = client.post(
        "/api/asr/transcribe",
        content=b"fake-audio",
        headers={"Content-Type": "audio/webm"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "语音输入占位文本"
    assert payload["provider"] == "stub"
    assert payload["confidence"] == 0.0
    assert payload["confidence_source"] == "stub"
    assert payload["needs_confirmation"] is True
    assert "ASR provider" in payload["error_message"]


def test_transcribe_audio_limits_size_from_settings() -> None:
    client = build_client(Settings(asr_provider="stub", asr_max_audio_bytes=1024))

    response = client.post(
        "/api/asr/transcribe",
        content=b"x" * 1025,
        headers={"Content-Type": "audio/webm"},
    )

    assert response.status_code == 413


def test_bailian_without_public_audio_base_returns_clear_degradation() -> None:
    client = build_client(
        Settings(
            asr_provider="bailian",
            asr_api_key="test-key",
            asr_public_audio_base_url="",
        )
    )

    response = client.post(
        "/api/asr/transcribe",
        content=b"fake-audio",
        headers={"Content-Type": "audio/webm"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "bailian_unavailable"
    assert payload["confidence_source"] == "unavailable"
    assert payload["needs_confirmation"] is True
    assert "公网访问" in payload["error_message"]
