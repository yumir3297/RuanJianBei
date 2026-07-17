from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FeedbackCreate(BaseModel):
    chat_log_id: int = Field(ge=1)
    session_id: str = Field(min_length=1, max_length=100)
    rating: Literal["positive", "negative"]
    reason_code: Literal["accuracy", "detail", "recommendation", "latency", "other"] | None = None
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_reason_for_negative_feedback(self) -> "FeedbackCreate":
        if self.rating == "negative" and not self.reason_code:
            raise ValueError("Negative feedback requires a reason_code.")
        return self


class FeedbackResponse(BaseModel):
    id: int
    rating: str
    message: str


class ExperienceTrendItem(BaseModel):
    date: str
    positive: int
    negative: int
    satisfaction_rate: float | None = None


class ExperienceTopicItem(BaseModel):
    label: str
    count: int


class ExperienceSuggestion(BaseModel):
    level: Literal["attention", "optimize", "keep"]
    title: str
    detail: str


class ExperienceReport(BaseModel):
    range: str
    data_mode: Literal["real", "demo", "empty"]
    generated_at: datetime
    service_sessions: int
    interaction_count: int
    feedback_count: int
    feedback_coverage: float
    satisfaction_rate: float | None = None
    positive_count: int
    negative_count: int
    sentiment_summary: str
    trend: list[ExperienceTrendItem]
    hot_questions: list[ExperienceTopicItem]
    negative_reasons: list[ExperienceTopicItem]
    suggestions: list[ExperienceSuggestion]
