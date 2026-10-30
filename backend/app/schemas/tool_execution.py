from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolTarget(StrictModel):
    type: Literal["tour_session"] = "tour_session"
    id: str = Field(min_length=1, max_length=36)
    base_revision: int = Field(ge=1)
    progress_version: int | None = Field(default=None, ge=0)
    content_digest: str | None = Field(default=None, min_length=64, max_length=64)


class ToolPrincipal(StrictModel):
    type: Literal["tourist"] = "tourist"
    id: str = Field(min_length=1, max_length=100)


class ToolStepView(StrictModel):
    key: str
    status: str
    attempt_count: int
    max_attempts: int
    error_code: str | None = None
    result: Any = None


class ToolJobView(StrictModel):
    id: str
    site_id: str
    target_type: str
    target_id: str
    tool_name: str
    tool_version: str
    workflow_schema_version: str
    recovery_mode: Literal["query_only", "manual_retry", "durable_resume"] = "durable_resume"
    retry_safe: bool = False
    input_digest: str
    base_revision: int
    progress_version: int | None = None
    content_digest: str | None = None
    status: str
    reason: str | None = None
    progress: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    event_seq: int = 0
    steps: list[ToolStepView] = Field(default_factory=list)


class ToolEventView(StrictModel):
    seq: int
    type: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ToolEventPage(StrictModel):
    items: list[ToolEventView]
    next_seq: int
    latest_seq: int
    snapshot_required: bool = False


class ToolRetryRequest(StrictModel):
    confirm_duplicate_risk: bool = False
