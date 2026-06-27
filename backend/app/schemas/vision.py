from __future__ import annotations

from pydantic import BaseModel, Field


class VisionAnalyzeResponse(BaseModel):
    scene_summary: str = ""
    detected_text: str = ""
    candidate_attractions: list[str] = Field(default_factory=list)
    visual_tags: list[str] = Field(default_factory=list)
    query_hints: list[str] = Field(default_factory=list)
    retrieval_query: str = ""
    confidence: float = 0.0
    provider: str = "stub"
