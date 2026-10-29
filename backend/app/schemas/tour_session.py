from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TourStop(BaseModel):
    spot_id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=160)
    resolved: bool = False
    published_content_version: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("景点名称不能为空")
        return value


class TourConstraints(BaseModel):
    companions: list[str] = Field(default_factory=list, max_length=12)
    available_minutes: int | None = Field(default=None, ge=1, le=720)
    interests: list[str] = Field(default_factory=list, max_length=20)
    required_spots: list[str] = Field(default_factory=list, max_length=50)
    excluded_spots: list[str] = Field(default_factory=list, max_length=50)
    walking_preference: str | None = Field(default=None, max_length=100)


class TourSourceReference(BaseModel):
    source_type: Literal["preset_route", "recommendation", "published_content"]
    source_id: str = Field(min_length=1, max_length=100)
    label: str = Field(default="", max_length=160)
    content_version: str | None = Field(default=None, max_length=100)


class TourSnapshot(BaseModel):
    constraints: TourConstraints = Field(default_factory=TourConstraints)
    stops: list[TourStop] = Field(default_factory=list, max_length=50)
    source: Literal["manual", "preset", "recommendation"] = "manual"
    source_references: list[TourSourceReference] = Field(default_factory=list, max_length=20)


class CreateTourSessionRequest(BaseModel):
    title: str = Field(default="我的游览", min_length=1, max_length=160)
    snapshot: TourSnapshot = Field(default_factory=TourSnapshot)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("游览名称不能为空")
        return value


class SaveTourSessionRequest(BaseModel):
    expected_version: int = Field(ge=1)
    snapshot: TourSnapshot


class TourArtifactReferenceRequest(BaseModel):
    revision_id: str | None = Field(default=None, max_length=36)
    artifact_type: Literal["itinerary", "narration", "recognition", "summary"]
    artifact_id: str = Field(min_length=1, max_length=100)
