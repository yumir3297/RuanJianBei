from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QACacheEntry(Base):
    __tablename__ = "qa_cache_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    normalized_query: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

