"""Stable, non-secret identifiers for generated speech and replay caching."""

from __future__ import annotations

import hashlib
import json

from app.core.config import Settings
from app.services.tts.factory import resolve_voice_for_provider


def answer_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_speech_profile(
    settings: Settings,
    preset: str | None = None,
    *,
    voice_override: str | None = None,
) -> dict[str, object]:
    provider = settings.tts_provider
    if provider == "volcengine":
        model = settings.volcengine_tts_resource_id
        output_format = settings.volcengine_tts_format
        sample_rate = settings.volcengine_tts_sample_rate
        endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    else:
        model = settings.tts_model
        output_format = "mp3"
        sample_rate = 24000
        endpoint = settings.tts_base_url

    endpoint_fingerprint = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    values: dict[str, object] = {
        "provider": provider,
        "model": model,
        "voice_preset": preset,
        "voice_id": voice_override or resolve_voice_for_provider(settings, preset),
        "format": output_format,
        "sample_rate": sample_rate,
        "rate": 100,
        "configured": settings.tts_ready,
        "endpoint_fingerprint": endpoint_fingerprint,
    }
    profile_fingerprint = hashlib.sha256(
        json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**values, "profile_hash": profile_fingerprint}


def build_speech_cache_key(text, profile):
    identity = {
        "answer_version": answer_fingerprint(text),
        "profile_hash": profile["profile_hash"],
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
