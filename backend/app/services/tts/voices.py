from __future__ import annotations


# 音色预设表：按 TTS provider 分组。
# 键为前端/管理端使用的音色类型（gentle-female 等），值为各 provider 的音色 ID。
TTS_VOICE_PRESETS: dict[str, dict[str, str]] = {
    # 火山豆包 TTS（seed-tts-2.0 系列，官方音色列表核实）
    "volcengine": {
        "gentle-female": "zh_female_cancan_uranus_bigtts",  # 知性灿灿 2.0
        "calm-female": "zh_female_zhixingnv_uranus_bigtts",  # 知性女声 2.0
        "deep-male": "zh_male_ruyaqingnian_uranus_bigtts",  # 儒雅青年 2.0
        "lively-female": "zh_female_kailangjiejie_uranus_bigtts",  # 开朗姐姐 2.0
    },
    # 百炼 CosyVoice（保留兼容，便于回退）
    "bailian": {
        "gentle-female": "longwan_v3",
        "calm-female": "longxiaoxia_v3",
        "deep-male": "longsanshu_v3",
        "lively-female": "longanqin_v3",
    },
}


def resolve_tts_voice(preset: str | None, fallback: str, provider: str = "volcengine") -> str:
    """按 provider 的预设表把音色类型解析为音色 ID；未知 preset 回退到 fallback。"""
    return TTS_VOICE_PRESETS.get(provider, {}).get(preset or "", fallback)
