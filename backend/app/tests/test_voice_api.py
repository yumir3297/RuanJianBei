from __future__ import annotations

import io
import wave
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.voice import router
from app.api.voice import get_asr_service
from app.core.config import Settings, get_settings
from app.services.asr.base import ASRResult
from app.services.asr.bailian import BailianASRService
import app.api.voice as voice_api


def build_client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/asr")
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_bailian_is_the_configured_cloud_asr_adapter() -> None:
    service = get_asr_service(Settings(asr_provider="bailian", asr_model="fun-asr"))
    assert isinstance(service, BailianASRService)


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


def test_transcription_idempotency_reuses_result_and_rejects_key_mismatch(monkeypatch) -> None:
    class CountingASR:
        calls = 0
        async def transcribe(self, payload):
            self.calls += 1
            return ASRResult(text="识别结果", confidence=0.9, provider="fake")
        async def aclose(self):
            return None

    service = CountingASR()
    client = build_client(Settings(asr_provider="bailian"))
    app = client.app
    app.dependency_overrides[get_asr_service] = lambda: service

    async def short_probe(*args, **kwargs):
        return 1

    monkeypatch.setattr(voice_api, "probe_audio_duration", short_probe)
    headers = {"Content-Type": "audio/webm", "Idempotency-Key": "voice-test-key"}
    first = client.post("/api/asr/transcribe", content=b"one", headers=headers)
    retry = client.post("/api/asr/transcribe", content=b"one", headers=headers)
    conflict = client.post("/api/asr/transcribe", content=b"two", headers=headers)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert conflict.status_code == 409
    assert service.calls == 1


def test_compressed_audio_duration_is_checked_before_provider(monkeypatch) -> None:
    class CountingASR:
        calls = 0
        async def transcribe(self, payload):
            self.calls += 1
            return ASRResult(text="ok", provider="fake")
        async def aclose(self):
            return None

    service = CountingASR()
    client = build_client(Settings(asr_provider="bailian", asr_max_audio_seconds=2))
    client.app.dependency_overrides[get_asr_service] = lambda: service

    async def short_probe(*args, **kwargs):
        return 1.5

    monkeypatch.setattr(voice_api, "probe_audio_duration", short_probe)
    allowed = client.post("/api/asr/transcribe", content=b"compressed", headers={"Content-Type": "audio/webm"})

    async def long_probe(*args, **kwargs):
        return 3.0

    monkeypatch.setattr(voice_api, "probe_audio_duration", long_probe)
    too_long = client.post("/api/asr/transcribe", content=b"compressed-long", headers={"Content-Type": "audio/webm"})
    assert allowed.status_code == 200
    assert too_long.status_code == 413
    assert service.calls == 1


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


def _wav(seconds: float) -> bytes:
    data = io.BytesIO()
    with wave.open(data, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * int(8000 * seconds))
    return data.getvalue()


def test_audio_rejects_invalid_wav_before_calling_provider() -> None:
    client = build_client(Settings(asr_provider="stub"))
    response = client.post("/api/asr/transcribe", content=b"not a wav", headers={"Content-Type": "audio/wav"})
    assert response.status_code == 400


def test_audio_enforces_wav_duration_limit() -> None:
    client = build_client(Settings(asr_provider="stub", asr_max_audio_seconds=1))
    response = client.post("/api/asr/transcribe", content=_wav(2), headers={"Content-Type": "audio/wav"})
    assert response.status_code == 413


def test_audio_accepts_real_wav_within_duration_limit() -> None:
    client = build_client(Settings(asr_provider="stub", asr_max_audio_seconds=1))
    response = client.post("/api/asr/transcribe", content=_wav(0.5), headers={"Content-Type": "audio/wav"})
    assert response.status_code == 200


def test_wav_cannot_bypass_duration_by_claiming_webm() -> None:
    client = build_client(Settings(asr_provider="stub", asr_max_audio_seconds=1))
    response = client.post("/api/asr/transcribe", content=_wav(2), headers={"Content-Type": "audio/webm"})
    assert response.status_code in {413, 415}
