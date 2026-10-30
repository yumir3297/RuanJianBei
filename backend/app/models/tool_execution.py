from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ToolJob(Base):
    __tablename__ = "tool_jobs"
    __table_args__ = (
        Index("ix_tool_jobs_claim", "status", "next_run_at", "created_at"),
        Index("ix_tool_jobs_target", "target_type", "target_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    site_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tour_sessions.id", ondelete="CASCADE"), nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_version: Mapped[str] = mapped_column(String(40), nullable=False)
    workflow_schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    recovery_mode: Mapped[str] = mapped_column(String(24), default="durable_resume", nullable=False)
    retry_safe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    progress_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    fence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolStep(Base):
    __tablename__ = "tool_steps"
    __table_args__ = (
        UniqueConstraint("job_id", "step_key", name="uq_tool_steps_job_key"),
        Index("ix_tool_steps_job_status", "job_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    external_state: Mapped[str] = mapped_column(String(24), default="not_started", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolAttempt(Base):
    __tablename__ = "tool_attempts"
    __table_args__ = (UniqueConstraint("step_id", "attempt_number", name="uq_tool_attempt_step_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("tool_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_state: Mapped[str] = mapped_column(String(24), default="not_started", nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class ToolEvent(Base):
    __tablename__ = "tool_events"
    __table_args__ = (UniqueConstraint("job_id", "seq", name="uq_tool_events_job_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ToolCommandReceipt(Base):
    __tablename__ = "tool_command_receipts"
    __table_args__ = (
        UniqueConstraint("principal_type", "principal_id", "command", "key", name="uq_tool_receipt_scope_key"),
        Index("ix_tool_command_receipts_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    command: Mapped[str] = mapped_column(String(40), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
