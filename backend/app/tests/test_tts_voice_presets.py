from app.services.tts.voices import TTS_VOICE_PRESETS, resolve_tts_voice


def test_presets_grouped_by_provider() -> None:
    """预设表按 provider 分组：火山豆包为主，百炼保留兼容。"""
    assert set(TTS_VOICE_PRESETS) == {"volcengine", "bailian"}


def test_volcengine_presets_use_doubao_voice_ids() -> None:
    volc = TTS_VOICE_PRESETS["volcengine"]
    assert set(volc) == {"gentle-female", "calm-female", "deep-male", "lively-female"}
    assert len(set(volc.values())) == 4
    for voice_id in volc.values():
        # 豆包 2.0 音色 ID 形如 zh_female_cancan_uranus_bigtts
        assert voice_id.startswith("zh_")
        assert voice_id.endswith("_bigtts")


def test_resolve_tts_voice_volcengine_maps_to_doubao() -> None:
    assert resolve_tts_voice("gentle-female", "fallback", provider="volcengine") == (
        "zh_female_cancan_uranus_bigtts"
    )
    assert resolve_tts_voice("calm-female", "fallback", provider="volcengine") == (
        "zh_female_zhixingnv_uranus_bigtts"
    )
    assert resolve_tts_voice("deep-male", "fallback", provider="volcengine") == (
        "zh_male_ruyaqingnian_uranus_bigtts"
    )
    assert resolve_tts_voice("lively-female", "fallback", provider="volcengine") == (
        "zh_female_kailangjiejie_uranus_bigtts"
    )


def test_resolve_tts_voice_keeps_bailian_for_compat() -> None:
    assert resolve_tts_voice("gentle-female", "fallback", provider="bailian") == "longwan_v3"
    assert resolve_tts_voice("calm-female", "fallback", provider="bailian") == "longxiaoxia_v3"
    assert resolve_tts_voice("deep-male", "fallback", provider="bailian") == "longsanshu_v3"
    assert resolve_tts_voice("lively-female", "fallback", provider="bailian") == "longanqin_v3"


def test_unknown_voice_uses_configured_fallback() -> None:
    assert resolve_tts_voice("unknown", "fallback-voice", provider="volcengine") == "fallback-voice"
    assert resolve_tts_voice(None, "fallback-voice", provider="volcengine") == "fallback-voice"
