from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictGuideLoopModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionContext(StrictGuideLoopModel):
    text: str = Field(min_length=1, max_length=280)
    poi_id: str | None = Field(default=None, max_length=64)
    target_id: str | None = Field(default=None, max_length=100)
    unit_id: str | None = Field(default=None, max_length=100)
    queried_date: str | None = Field(default=None, max_length=32)


class MatchDecision(StrictGuideLoopModel):
    decision: Literal["reuse", "distinct", "clarify"]
    reason_code: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0.0, le=1.0)


GuideLoopCategory = Literal[
    "missing_fact",
    "retrieval_gap",
    "explanation_gap",
    "stale_or_conflict",
    "technical",
    "unknown",
]


class ObservationCreate(StrictGuideLoopModel):
    event_id: str = Field(min_length=1, max_length=100)
    session_key: str = Field(min_length=1, max_length=100)
    cluster_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=280)
    queried_date: date | None = None
    poi_id: str | None = Field(default=None, max_length=64)
    target_id: str | None = Field(default=None, max_length=100)
    unit_id: str | None = Field(default=None, max_length=100)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    result_code: Literal["unanswered", "correction", "followup", "technical_error"]
    category: GuideLoopCategory = "unknown"
    replay_id: str = Field(min_length=1, max_length=100)
    origin: Literal["synthetic", "consented_redacted"]


class ObservationRead(StrictGuideLoopModel):
    event_id: str
    cluster_id: str
    requested_cluster_id: str
    replay_id: str
    clarification_required: bool = False
    reason_code: str | None = None
    duplicate: bool = False


class GuideLoopCaseRead(StrictGuideLoopModel):
    cluster_id: str
    category: GuideLoopCategory
    status: Literal["open", "draft", "verified", "published_pending_check", "closed", "reopened"]
    observation_count: int
    distinct_session_count: int
    sample_questions: list[str]
    replay_ids: list[str]
    clarification_required: bool = False
    clarification_reasons: list[str] = Field(default_factory=list)
    draft_id: str | None = None
    draft: dict | None = None
    verification: dict | None = None
    active_revision_id: str | None = None


class DraftRequest(StrictGuideLoopModel):
    base_revision: str = Field(min_length=1, max_length=100)
    action: Literal["add_alias", "replace_fact", "withdraw"]
    poi_id: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=100)
    alias: str | None = Field(default=None, max_length=280)
    answer: str | None = Field(default=None, max_length=2000)
    evidence: dict[str, str] = Field(min_length=2)
    knowledge_entry_id: int | None = Field(default=None, gt=0)
    knowledge_revision_id: str | None = Field(default=None, min_length=1, max_length=36)
    effective_from: str = Field(min_length=1, max_length=40)
    effective_until: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_knowledge_reference(self):
        if (self.knowledge_entry_id is None) != (self.knowledge_revision_id is None):
            raise ValueError("knowledge entry and revision must be supplied together")
        return self


class VerifyRequest(StrictGuideLoopModel):
    draft_id: str = Field(min_length=1, max_length=100)


class PublishRequest(StrictGuideLoopModel):
    draft_id: str = Field(min_length=1, max_length=100)
    base_revision: str = Field(min_length=1, max_length=100)
    source_reviewed: bool = False


class ConfirmLiveRequest(StrictGuideLoopModel):
    check_id: str = Field(min_length=1, max_length=100)
    passed: bool


class GuideLoopContext(StrictGuideLoopModel):
    poi_id: str = Field(min_length=1, max_length=64)
    unit_id: str | None = Field(default=None, max_length=100)
