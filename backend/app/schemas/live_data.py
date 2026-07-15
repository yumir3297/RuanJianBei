from __future__ import annotations

from pydantic import BaseModel, Field


class AttractionLiveStatus(BaseModel):
    attraction_id: str
    name: str
    status: str
    note: str = ""


class LiveContext(BaseModel):
    is_mock: bool = True
    source_label: str = "mock"
    weather: dict[str, str] = Field(default_factory=dict)
    visitor_flow: dict[str, str] = Field(default_factory=dict)
    attractions_status: list[AttractionLiveStatus] = Field(default_factory=list)
    timestamp: str = ""
