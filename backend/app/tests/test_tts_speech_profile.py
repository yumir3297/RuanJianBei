import hashlib
import json

from app.core.config import Settings
from app.services.tts.speech_profile import build_speech_profile, build_speech_cache_key, answer_fingerprint


def test_speech_profile_records_only_allowlisted_generation_parameters():
    settings = Settings(
        tts_provider="bailian",
        tts_api_key="must-not-persist",
        tts_model="cosyvoice-v3-flash",
        tts_base_url="https://tts.example/api",
    )

    profile = build_speech_profile(settings, "deep-male")

    assert profile["provider"] == "bailian"
    assert profile["model"] == "cosyvoice-v3-flash"
    assert profile["voice_preset"] == "deep-male"
    assert profile["format"] == "mp3"
    assert profile["sample_rate"] == 24000
    assert profile["rate"] == 100
    assert "must-not-persist" not in json.dumps(profile)
    assert "tts_api_key" not in profile
    assert profile["profile_hash"] == build_speech_profile(settings, "deep-male")["profile_hash"]


def test_speech_profile_hash_changes_when_any_synthesis_parameter_changes():
    baseline = Settings(tts_provider="bailian", tts_model="model-a", tts_api_key="secret")
    changed_model = Settings(tts_provider="bailian", tts_model="model-b", tts_api_key="secret")
    changed_provider = Settings(
        tts_provider="volcengine",
        volcengine_tts_api_key="secret",
        volcengine_tts_resource_id="seed-tts-2.0",
    )
    changed_sample_rate = Settings(
        tts_provider="volcengine",
        volcengine_tts_api_key="secret",
        volcengine_tts_resource_id="seed-tts-2.0",
        volcengine_tts_sample_rate=16000,
    )

    profile = build_speech_profile(baseline, "gentle-female")
    assert profile["profile_hash"] != build_speech_profile(changed_model, "gentle-female")["profile_hash"]
    assert profile["profile_hash"] != build_speech_profile(changed_provider, "gentle-female")["profile_hash"]
    assert build_speech_profile(changed_provider, "gentle-female")["profile_hash"] != build_speech_profile(
        changed_sample_rate, "gentle-female"
    )["profile_hash"]
    assert profile["profile_hash"] != build_speech_profile(baseline, "deep-male")["profile_hash"]


def test_answer_version_and_cache_key_bind_text_to_complete_profile():
    settings = Settings(tts_provider="bailian", tts_model="model-a", tts_api_key="secret")
    first = build_speech_profile(settings, "gentle-female")
    other_voice = build_speech_profile(settings, "deep-male")
    text = "保存的回答"

    assert answer_fingerprint(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert build_speech_cache_key(text, first) != build_speech_cache_key("不同回答", first)
    assert build_speech_cache_key(text, first) != build_speech_cache_key(text, other_voice)
