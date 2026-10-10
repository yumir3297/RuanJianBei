from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.selection import SelectionContext


class ConversationContext(BaseModel):
    last_subject: str | None = None
    history_summary: str | None = None


class VisionContext(BaseModel):
    scene_summary: str = ""
    candidate_attractions: list[str] = Field(default_factory=list)
    visual_tags: list[str] = Field(default_factory=list)
    retrieval_query: str = ""
    confidence: float = 0.0


class EmotionContext(BaseModel):
    audio_emotion: Literal[
        "positive",
        "neutral",
        "confused",
        "dissatisfied",
        "anxious",
        "urgent",
    ] | None = None
    audio_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    audio_source: str | None = Field(default=None, max_length=50)
    audio_event: str | None = Field(default=None, max_length=100)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(min_length=1, max_length=100)
    input_mode: Literal["text", "voice"] = "text"
    text_only: bool = False
    persona: Literal["hanfu", "monk", "modern"] | None = None
    audience: Literal["child", "adult", "expert"] | None = None
    """讲解口径（分众化）：儿童易懂 / 常规 / 文化深度。与 SelectionContext.audience_type
    （路线推荐人群画像 family/culture/free/leisure/general）是两个独立概念，不要合并。"""
    visitor_id: str | None = Field(default=None, min_length=1, max_length=64)
    """稳定的匿名游客标识（前端 localStorage 生成），用于跨会话记忆；不承载任何身份信息。"""
    tts_voice: Literal[
        "gentle-female",
        "calm-female",
        "deep-male",
        "lively-female",
    ] | None = None
    tts_rate: int = Field(default=100, ge=80, le=150)
    tts_volume: int = Field(default=80, ge=0, le=100)
    context: ConversationContext | None = None
    selection: SelectionContext | None = None
    vision_context: VisionContext | None = None
    emotion_context: EmotionContext | None = None


class SourceItem(BaseModel):
    evidence_id: str | None = None
    title: str
    snippet: str
    source: str
    score: float | None = None


class StreamEventPayload(BaseModel):
    type: str
    data: dict[str, Any]
