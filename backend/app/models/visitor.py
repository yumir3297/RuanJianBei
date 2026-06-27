from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VisitorProfile(Base):
    __tablename__ = "visitor_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    preference_tags: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    audience_type: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

