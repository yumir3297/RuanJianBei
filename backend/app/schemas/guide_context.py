from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class LocationHint(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100_000)
    observed_at: str | None = Field(default=None, max_length=64)
    coordinate_system: Literal["WGS84", "GCJ-02"]
    mode: Literal["real", "sim", "denied", "unavailable"]


class GuidePreferences(StrictModel):
    interests: list[str] = Field(default_factory=list, max_length=8)
    remaining_minutes: int | None = Field(default=None, ge=1, le=720)
    proactive_enabled: bool = True

    @field_validator("interests")
    @classmethod
    def trim_interests(cls, values: list[str]) -> list[str]:
        allowed = {"history", "nature", "architecture", "culture", "family", "photography", "food"}
        return list(dict.fromkeys(value for value in values if value in allowed))


class GuideDecisionRequest(StrictModel):
    snapshot_id: str | None = Field(default=None, max_length=100)
    spot_code: str | None = Field(default=None, max_length=100)
    published_revision_id: str | None = Field(default=None, max_length=100)
    catalog_digest: str | None = Field(default=None, max_length=128)
    location_hint: LocationHint | None = None
    preferences: GuidePreferences = Field(default_factory=GuidePreferences)
    tour_session_id: str | None = Field(default=None, max_length=100)
    expected_tour_version: int | None = Field(default=None, ge=1)
    progress_version: int | None = Field(default=None, ge=1)
    demo_scenario_id: str | None = Field(default=None, max_length=100)
    playback_busy: bool = False
