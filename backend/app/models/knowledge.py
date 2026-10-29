from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_revisions.id", use_alter=True, name="fk_knowledge_published_revision"), nullable=True
    )
    draft_revision_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_revisions.id", use_alter=True, name="fk_knowledge_draft_revision"), nullable=True
    )
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
