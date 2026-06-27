from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RouteTemplate(Base):
    __tablename__ = "route_templates"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    duration_label: Mapped[str] = mapped_column(String(100), nullable=False)
    route_plan: Mapped[str] = mapped_column(Text, nullable=False)
    guide_points_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    experiences_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
