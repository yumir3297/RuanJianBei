import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.services.tts.base import TTSAudio
from app.services.tts.replay_cache import ReplayAudioCache


class _FakeTTS:
    def __init__(self, calls):
        self.calls = calls

    async def synthesize(self, text):
        self.calls.append(text)
        return TTSAudio("encoded-audio", 1234, "fake-provider")


def _client(monkeypatch, *, tts_ready=False, speech_metadata=None):
    app = FastAPI()
    app.include_router(chat_api.router, prefix="/api/chat")
    app.state.guide_capacity = None

    async def override_session():
        return object()

    def override_settings():
        if tts_ready:
            return Settings(tts_provider="bailian", tts_api_key="test-key")
        return Settings(tts_provider="stub")

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_app_settings] = override_settings
    calls = []
    factory_calls = []

    async def find_log(_repository, chat_log_id, session_id):
        if chat_log_id == 17 and session_id == "owned-session":
            encoded_metadata = (
                json.dumps(speech_metadata, ensure_ascii=False)
                if speech_metadata is not None
                else None
            )
            return SimpleNamespace(answer="数据库保存的原回答", speech_metadata=encoded_metadata)
        return None

    def build_tts(_settings, *, preset=None, voice_override=None):
        factory_calls.append({"preset": preset, "voice_override": voice_override})
        return _FakeTTS(calls)

    monkeypatch.setattr(chat_api.ChatLogRepository, "get_for_session", find_log)
    monkeypatch.setattr(chat_api, "_replay_audio_cache", ReplayAudioCache())
    monkeypatch.setattr(chat_api, "build_tts_service", build_tts)
    monkeypatch.setattr(
        chat_api,
        "build_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("QA pipeline must not run")),
    )
    return TestClient(app), calls, factory_calls


def test_replay_synthesizes_saved_answer_without_running_qa_pipeline(monkeypatch):
    client, calls, factory_calls = _client(
        monkeypatch,
        tts_ready=True,
        speech_metadata={
            "provider": "bailian",
            "model": "cosyvoice-v3-flash",
            "voice_preset": "deep-male",
            "voice_id": "longsanshu_v3",
        },
    )

    response = client.post(
        "/api/chat/replay",
        json={"chat_log_id": 17, "session_id": "owned-session", "tts_voice": "deep-male"},
    )

    assert response.status_code == 200
    assert calls == ["数据库保存的原回答"]
    assert factory_calls == [{"preset": "deep-male", "voice_override": "longsanshu_v3"}]
    assert response.json() == {
        "base64_audio": "encoded-audio",
        "duration_ms": 1234,
        "provider": "fake-provider",
        "available": True,
    }


def test_replay_returns_unavailable_when_tts_is_not_configured(monkeypatch):
    client, calls, _factory_calls = _client(monkeypatch)

    response = client.post(
        "/api/chat/replay",
        json={"chat_log_id": 17, "session_id": "owned-session"},
    )

    assert response.status_code == 200
    assert calls == []
    assert response.json() == {
        "base64_audio": "",
        "duration_ms": 0,
        "provider": "tts_not_configured",
        "available": False,
    }


def test_replay_hides_logs_from_other_sessions_without_synthesizing(monkeypatch):
    client, calls, _factory_calls = _client(monkeypatch, tts_ready=True)

    response = client.post(
        "/api/chat/replay",
        json={"chat_log_id": 17, "session_id": "other-session"},
    )

    assert response.status_code == 404
    assert calls == []


def test_replay_rejects_unknown_voice_preset(monkeypatch):
    client, _calls, _factory_calls = _client(monkeypatch, tts_ready=True)

    response = client.post(
        "/api/chat/replay",
        json={"chat_log_id": 17, "session_id": "owned-session", "tts_voice": "unknown"},
    )

    assert response.status_code == 422


def test_replay_uses_current_requested_voice_for_legacy_logs_without_metadata(monkeypatch):
    client, _calls, factory_calls = _client(monkeypatch, tts_ready=True, speech_metadata=None)

    response = client.post(
        "/api/chat/replay",
        json={"chat_log_id": 17, "session_id": "owned-session", "tts_voice": "gentle-female"},
    )

    assert response.status_code == 200
    assert factory_calls == [{"preset": "gentle-female", "voice_override": None}]


def test_replay_reuses_cached_audio_for_same_answer_and_profile(monkeypatch):
    client, calls, _factory_calls = _client(monkeypatch, tts_ready=True)
    payload = {"chat_log_id": 17, "session_id": "owned-session", "tts_voice": "deep-male"}

    first = client.post("/api/chat/replay", json=payload)
    second = client.post("/api/chat/replay", json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == ["数据库保存的原回答"]
