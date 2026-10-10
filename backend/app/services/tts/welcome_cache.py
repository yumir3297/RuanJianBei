"""Welcome audio cache — pre-generates the greeting TTS audio for each avatar."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.tts.base import TTSAudio
from app.services.tts.factory import build_tts_service

logger = logging.getLogger(__name__)

MODEL_NAMES = {
    "monk": "宁灵",
    "hanfu": "清岚",
    "modern": "景行",
}

_welcome_cache: dict[str, TTSAudio] = {}


def get_welcome_text(model_key: str) -> str:
    name = MODEL_NAMES.get(model_key, "小灵")
    scenic_name = get_settings().scenic_name
    return f"您好！我是{scenic_name}智慧导游{name}，很高兴陪您一起游览。想了解景点故事、规划路线，或认一认眼前的风景，都可以问我。"


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


async def generate_and_cache(model_key: str, voice_type: str) -> TTSAudio:
    """Synthesize the welcome TTS audio and cache it in memory.

    TTS provider 与凭据统一从全局配置读取（工厂分发），
    调用方只关心角色与音色类型。
    """
    settings = get_settings()
    text = get_welcome_text(model_key)

    try:
        service = build_tts_service(settings, preset=voice_type)
    except Exception:
        logger.exception("Welcome audio TTS unavailable (provider=%s)", settings.tts_provider)
        return TTSAudio(
            base64_audio="",
            duration_ms=0,
            provider=f"{settings.tts_provider}_unavailable",
        )

    try:
        audio = await service.synthesize(text)
    except Exception:
        logger.exception("Welcome audio TTS synthesis failed")
        return TTSAudio(
            base64_audio="",
            duration_ms=0,
            provider=f"{settings.tts_provider}_unavailable",
        )

    if not audio.base64_audio:
        logger.warning("Welcome audio TTS returned empty audio")
        return audio

    key = _cache_key(model_key, voice_type)
    _welcome_cache[key] = audio
    logger.info(
        "Welcome audio cached for model=%s voice=%s (%d ms)",
        model_key,
        voice_type,
        audio.duration_ms,
    )
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
