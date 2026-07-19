from __future__ import annotations


TTS_VOICE_PRESETS = {
    "gentle-female": "longwan_v3",
    "calm-female": "longxiaoxia_v3",
    "deep-male": "longsanshu_v3",
    "lively-female": "longanqin_v3",
}


def resolve_tts_voice(preset: str | None, fallback: str) -> str:
    return TTS_VOICE_PRESETS.get(preset or "", fallback)
