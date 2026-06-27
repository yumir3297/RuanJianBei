from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeBlindSpot(Base):
    __tablename__ = "knowledge_blind_spots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    normalized_query: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    raw_query_samples_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    resolution_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_faq_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved_knowledge_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
