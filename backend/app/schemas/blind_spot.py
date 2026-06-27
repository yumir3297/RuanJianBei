from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BlindSpotRead(BaseModel):
    id: int
    normalized_query: str
    raw_query_samples: list[str]
    hit_count: int
    status: Literal["open", "resolved"]
    category: str
    resolution_type: str | None
    resolved_faq_id: str | None
    resolved_knowledge_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None


class ResolveBlindSpotWithFAQRequest(BaseModel):
    faq_id: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=50)
    aliases: list[str] = Field(min_length=1, max_length=20)
    answer: str = Field(min_length=1, max_length=10000)
    sources: list[str] = Field(min_length=1, max_length=20)

    @field_validator("faq_id", "category", "answer")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped

    @field_validator("aliases", "sources")
    @classmethod
    def clean_required_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            stripped = value.strip()
            if not stripped:
                continue
            key = stripped.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(stripped)
        if not cleaned:
            raise ValueError("list must contain at least one non-blank value")
        return cleaned


class BlindSpotResolutionResponse(BaseModel):
    message: str
    blind_spot: BlindSpotRead
    faq_id: str
    faq_reload_ms: float
    faq_index_count: int
    semantic_alias_count: int
