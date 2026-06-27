from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SelectionContext(BaseModel):
    mode: Literal["free_chat", "topic", "attraction", "route"] = "free_chat"
    attraction_id: int | None = Field(default=None, ge=1)
    topic_key: str | None = Field(default=None, min_length=1, max_length=50)
    route_id: str | None = Field(default=None, min_length=1, max_length=50)
    interests: list[str] = Field(default_factory=list, max_length=10)
    audience_type: str | None = Field(default=None, min_length=1, max_length=100)
    available_hours: int | None = Field(default=None, ge=1, le=12)
    avoid_crowded: bool | None = None


class QuickTopicRead(BaseModel):
    key: str
    label: str
    category: str
    icon: str
    sort_order: int


class AttractionOption(BaseModel):
    id: int
    title: str
    scenic_area: str | None = None
    attraction_code: str | None = None


class RouteOption(BaseModel):
    id: str
    title: str
    duration_label: str
    tags: list[str] = Field(default_factory=list)


class QuickSelectBootstrapResponse(BaseModel):
    topics: list[QuickTopicRead] = Field(default_factory=list)
    attractions: list[AttractionOption] = Field(default_factory=list)
    routes: list[RouteOption] = Field(default_factory=list)
