from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeRevision(Base):
    __tablename__ = "knowledge_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_entry_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_revisions.id"), nullable=True, index=True
    )
    source_document_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SourceDocumentVersion(Base):
    __tablename__ = "source_document_versions"
    __table_args__ = (UniqueConstraint("document_id", "sha256", name="uq_source_document_content"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=True
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ImportJob(Base):
    __tablename__ = "knowledge_import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ImportConflict(Base):
    __tablename__ = "knowledge_import_conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("knowledge_import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_entry_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_entries.id"), nullable=True, index=True)
    current_revision_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_revisions.id"), nullable=True)
    incoming_revision_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_revisions.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    resolution_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PublicationJob(Base):
    __tablename__ = "knowledge_publication_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(24), default="queued", nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PublicationItem(Base):
    __tablename__ = "knowledge_publication_items"
    __table_args__ = (UniqueConstraint("job_id", "knowledge_entry_id", name="uq_publication_entry"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("knowledge_publication_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_entry_id: Mapped[int] = mapped_column(ForeignKey("knowledge_entries.id"), nullable=False, index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("knowledge_revisions.id"), nullable=False, index=True)
    expected_lock_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), default="queued", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeState(Base):
    __tablename__ = "knowledge_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    epoch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
