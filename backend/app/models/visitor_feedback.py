from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VisitorFeedback(Base):
    """A visitor's explicit assessment of one answer.

    Demo records are deliberately kept in the same table as production records so
    the report exercises its real aggregation path. They are excluded as soon as
    real feedback becomes available.
    """

    __tablename__ = "visitor_feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
