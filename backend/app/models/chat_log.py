from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    hit_level: Mapped[str] = mapped_column(String(50), default="rag", nullable=False)
    latency_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    input_mode: Mapped[str] = mapped_column(String(20), default="text", nullable=False)
    text_emotion: Mapped[str] = mapped_column(String(30), default="neutral", nullable=False)
    audio_emotion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fused_emotion: Mapped[str] = mapped_column(String(30), default="neutral", nullable=False, index=True)
    emotion_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    emotion_intensity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    emotion_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    emotion_modalities: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    response_strategy: Mapped[str] = mapped_column(String(30), default="neutral", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
