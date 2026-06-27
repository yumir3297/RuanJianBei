from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general", max_length=100)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    metadata_json: str | None = None


class KnowledgeCreate(KnowledgeBase):
    pass


class KnowledgeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    content: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1, max_length=255)
    aliases: list[str] | None = None
    metadata_json: str | None = None


class KnowledgeRead(KnowledgeBase):
    id: int
    created_at: datetime
    updated_at: datetime
