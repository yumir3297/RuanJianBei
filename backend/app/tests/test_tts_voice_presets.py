from app.services.tts.voices import TTS_VOICE_PRESETS, resolve_tts_voice


def test_four_admin_voice_presets_map_to_distinct_provider_voices() -> None:
    assert set(TTS_VOICE_PRESETS) == {
        "gentle-female",
        "calm-female",
        "deep-male",
        "lively-female",
    }
    assert len(set(TTS_VOICE_PRESETS.values())) == 4
    assert resolve_tts_voice("gentle-female", "fallback") == "longwan_v3"
    assert resolve_tts_voice("calm-female", "fallback") == "longxiaoxia_v3"
    assert resolve_tts_voice("deep-male", "fallback") == "longsanshu_v3"
    assert resolve_tts_voice("lively-female", "fallback") == "longanqin_v3"


def test_unknown_voice_uses_configured_fallback() -> None:
    assert resolve_tts_voice("unknown", "fallback-voice") == "fallback-voice"
