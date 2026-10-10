from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VisitorMemory(Base):
    """跨会话游客记忆。

    与 VisitorProfile 的区别：VisitorProfile 以 session_id 为唯一键、每轮整体覆盖，
    只能表达"这一次会话"；本表以稳定 visitor_id 为唯一键、按景区隔离、逐轮累积，
    用于复访识别。两者并存，不要合并——VisitorProfile 仍服务于后台画像统计。
    """

    __tablename__ = "visitor_memories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    site_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False, index=True)
    visited_attractions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    preference_tags: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    narration_audience: Mapped[str] = mapped_column(String(20), default="adult", nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_session_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
