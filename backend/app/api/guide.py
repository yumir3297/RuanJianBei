"""景点自动讲解接口。

复用既有 QA pipeline（RAG + LLM）生成讲解词，再用其 TTS 服务合成整段音频：

- 走 ``stream_chat(text_only=True)`` 累积全文，不新增非流式 pipeline 方法。
- 结果按 ``景点|音色|模型`` 缓存并做 singleflight，二次靠近秒返回。
- 任何失败都降级为 ``available=False``，不抛 5xx，由前端改用静态简介 + 浏览器朗读。
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import build_pipeline
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.schemas.chat import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)

NARRATION_PROMPT = "请介绍{name}"

# pipeline 答案会带上风格化前缀与证据标记，讲解场景需要清理
# 风格化前缀形态多样（"好的，让我为您道来——" / "来，咱们看看——" / "根据官方资料记载——"），
# 统一按「开头一段不含句末标点、以 —— 收尾」的模式剥离。
_LEAD_STYLER_RE = re.compile(r"^[^。！？\n]{0,24}?——\s*")
# 检索降级时 pipeline 会插入一行说明，讲解场景直接去掉
_DEGRADED_LEAD_RE = re.compile(r"^AI讲解服务暂时不可用[^\n]*[:：]\s*")
_CITATION_RE = re.compile(r"[\[【]\s*(?:证据)?\s*\d+\s*[\]】]")
_NARRATION_CACHE: dict[str, dict[str, Any]] = {}
_LOCK_REGISTRY: dict[str, asyncio.Lock] = {}


class NarrationRequest(BaseModel):
    attraction: str = Field(min_length=1, max_length=50)
    tts_voice: str | None = None


def _cache_key(attraction: str, voice: str, model: str) -> str:
    return f"{attraction}|{voice}|{model}"


def _get_lock(key: str) -> asyncio.Lock:
    lock = _LOCK_REGISTRY.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _LOCK_REGISTRY[key] = lock
    return lock


def _clean(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = _DEGRADED_LEAD_RE.sub("", cleaned, count=1)
    cleaned = _LEAD_STYLER_RE.sub("", cleaned, count=1)
    cleaned = _CITATION_RE.sub("", cleaned)
    cleaned = cleaned.replace("**", "").replace("##", "")
    return cleaned.strip()


def _degraded(attraction: str, reason: str) -> dict[str, Any]:
    return {
        "attraction": attraction,
        "text": "",
        "base64_audio": "",
        "duration_ms": 0,
        "provider": "",
        "cached": False,
        "available": False,
        "reason": reason,
    }


async def _generate(
    session: AsyncSession,
    settings: Settings,
    attraction: str,
    tts_voice: str | None,
) -> dict[str, Any]:
    try:
        pipeline = await build_pipeline(session, settings, tts_voice_preset=tts_voice)
    except Exception:
        logger.exception("Narration pipeline build failed for %s", attraction)
        return _degraded(attraction, "pipeline_unavailable")

    text = ""
    try:
        request = ChatRequest(
            query=NARRATION_PROMPT.format(name=attraction),
            session_id=f"narration-{attraction}",
            text_only=True,
        )
        async for event in pipeline.stream_chat(request):
            if event.type == "text" and event.data.get("is_complete"):
                text = event.data.get("text") or text
    except Exception:
        logger.exception("Narration generation failed for %s", attraction)

    text = _clean(text)
    if not text:
        return _degraded(attraction, "llm_unavailable")

    base64_audio = ""
    duration_ms = 0
    provider = ""
    try:
        audio = await pipeline.tts_service.synthesize(text)
        base64_audio = audio.base64_audio
        duration_ms = audio.duration_ms
        provider = audio.provider
    except Exception:
        logger.exception("Narration TTS failed for %s", attraction)

    return {
        "attraction": attraction,
        "text": text,
        "base64_audio": base64_audio,
        "duration_ms": duration_ms,
        "provider": provider,
        "cached": False,
        "available": True,
        "reason": "" if base64_audio else "tts_unavailable",
    }


@router.post("/narration", summary="生成景点自动讲解文本与语音")
async def create_narration(
    payload: NarrationRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    attraction = payload.attraction.strip()
    voice = payload.tts_voice or settings.tts_voice
    key = _cache_key(attraction, voice, settings.llm_model or "stub")

    cached = _NARRATION_CACHE.get(key)
    if cached is not None:
        return {**cached, "cached": True}

    async with _get_lock(key):
        cached = _NARRATION_CACHE.get(key)
        if cached is not None:
            return {**cached, "cached": True}
        result = await _generate(session, settings, attraction, payload.tts_voice)
        if result["available"]:
            _NARRATION_CACHE[key] = result
        return result
