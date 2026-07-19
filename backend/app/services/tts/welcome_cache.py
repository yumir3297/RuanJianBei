"""Welcome audio cache — pre-generates the greeting TTS audio for each avatar."""

from __future__ import annotations

import logging

from app.services.tts.bailian import BailianTTSService
from app.services.tts.base import TTSAudio
from app.services.tts.voices import resolve_tts_voice

logger = logging.getLogger(__name__)

MODEL_NAMES = {
    "monk": "宁灵",
    "hanfu": "清岚",
    "modern": "景行",
}

_welcome_cache: dict[str, TTSAudio] = {}


def get_welcome_text(model_key: str) -> str:
    name = MODEL_NAMES.get(model_key, "小灵")
    return f"您好！我是灵山智慧导游{name}，很高兴陪您一起游览。想了解景点故事、规划路线，或认一认眼前的风景，都可以问我。"


def _derive_model_key(model_path: str) -> str:
    if "monk" in model_path:
        return "monk"
    if "hanfu" in model_path:
        return "hanfu"
    if "modern" in model_path:
        return "modern"
    return "hanfu"


def _cache_key(model_key: str, voice_type: str) -> str:
    return f"{model_key}:{voice_type}"


def get_cached(model_key: str, voice_type: str) -> TTSAudio | None:
    return _welcome_cache.get(_cache_key(model_key, voice_type))


async def generate_and_cache(
    model_key: str,
    voice_type: str,
    api_key: str,
    base_url: str,
    model: str,
    fallback_voice: str,
    timeout_seconds: float = 30.0,
) -> TTSAudio:
    """Synthesize the welcome TTS audio and cache it in memory."""
    text = get_welcome_text(model_key)
    provider_voice = resolve_tts_voice(voice_type, fallback_voice)

    try:
        audio = await BailianTTSService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            voice=provider_voice,
            timeout_seconds=timeout_seconds,
            use_compatible_api=False,
        ).synthesize(text)
    except Exception:
        logger.exception("Welcome audio TTS synthesis failed")
        return TTSAudio(base64_audio="", duration_ms=0, provider="bailian_unavailable")

    if not audio.base64_audio:
        logger.warning("Welcome audio TTS returned empty audio")
        return audio

    key = _cache_key(model_key, voice_type)
    _welcome_cache[key] = audio
    logger.info("Welcome audio cached for model=%s voice=%s (%d ms)", model_key, voice_type, audio.duration_ms)
    return audio


def invalidate_cache(model_key: str | None = None):
    """Clear cached welcome audio (all or for a specific model)."""
    global _welcome_cache
    if model_key is None:
        _welcome_cache = {}
    else:
        keys = [k for k in _welcome_cache if k.startswith(f"{model_key}:")]
        for k in keys:
            del _welcome_cache[k]
