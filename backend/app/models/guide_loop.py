from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GuideLoopCase(Base):
    __tablename__ = "guide_loop_cases"

    cluster_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    draft_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draft_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class GuideLoopRevision(Base):
    __tablename__ = "guide_loop_revisions"

    revision_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    base_revision: Mapped[str] = mapped_column(String(100), nullable=False)
    case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    poi_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(280), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    knowledge_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knowledge_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GuideLoopPointer(Base):
    __tablename__ = "guide_loop_pointers"

    scope_key: Mapped[str] = mapped_column(String(180), primary_key=True)
    poi_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    revision_id: Mapped[str] = mapped_column(String(100), nullable=False)


class GuideLoopCheck(Base):
    __tablename__ = "guide_loop_checks"

    check_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    revision_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    operator_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    operator_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GuideLoopObservation(Base):
    __tablename__ = "guide_loop_observations"
    __table_args__ = (
        Index("ix_guide_loop_observations_cluster_created", "cluster_id", "created_at"),
        Index("ix_guide_loop_observations_session_cluster", "session_key", "cluster_id"),
    )

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cluster_id: Mapped[str] = mapped_column(ForeignKey("guide_loop_cases.cluster_id", ondelete="CASCADE"), nullable=False)
    requested_cluster_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_key: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(String(280), nullable=False)
    queried_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    poi_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    result_code: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    replay_id: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[str] = mapped_column(String(30), nullable=False)
    match_decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
