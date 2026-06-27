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


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(min_length=1, max_length=100)
    input_mode: Literal["text", "voice"] = "text"
    text_only: bool = False
    persona: Literal["hanfu", "monk", "modern"] | None = None
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


class SourceItem(BaseModel):
    evidence_id: str | None = None
    title: str
    snippet: str
    source: str
    score: float | None = None


class StreamEventPayload(BaseModel):
    type: str
    data: dict[str, Any]
