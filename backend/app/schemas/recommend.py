from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    interests: list[str] = Field(default_factory=list)
    available_hours: int = Field(default=2, ge=1, le=12)
    audience_type: str = Field(default="general", max_length=100)
    avoid_crowded: bool = False


class RecommendItem(BaseModel):
    route_id: str
    title: str
    reason: str
    duration_hours: int
    duration_label: str
    route_plan: str
    guide_points: list[str] = Field(default_factory=list)
    experiences: list[str] = Field(default_factory=list)
    source: str


class RecommendResponse(BaseModel):
    routes: list[RecommendItem]
