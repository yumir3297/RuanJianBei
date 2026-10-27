"""add persistent knowledge revisions and workspace jobs

Revision ID: c84d0f1a7b92
Revises: a1c7f2d9b4e0
Create Date: 2026-10-27
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c84d0f1a7b92"
down_revision: Union[str, None] = "a1c7f2d9b4e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "source_document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_version_id", sa.String(36), sa.ForeignKey("source_document_versions.id"), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("parse_status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", "sha256", name="uq_source_document_content"),
    )
    op.create_index("ix_source_document_versions_document_id", "source_document_versions", ["document_id"])
    op.create_index("ix_source_document_versions_parse_status", "source_document_versions", ["parse_status"])

    op.create_table(
        "knowledge_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("knowledge_entry_id", sa.Integer(), sa.ForeignKey("knowledge_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_revision_id", sa.String(36), sa.ForeignKey("knowledge_revisions.id"), nullable=True),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("source_document_versions.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("aliases", sa.Text(), server_default="", nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_revisions_knowledge_entry_id", "knowledge_revisions", ["knowledge_entry_id"])
    op.create_index("ix_knowledge_revisions_base_revision_id", "knowledge_revisions", ["base_revision_id"])
    op.create_index("ix_knowledge_revisions_source_document_version_id", "knowledge_revisions", ["source_document_version_id"])
    op.create_index("ix_knowledge_revisions_content_hash", "knowledge_revisions", ["content_hash"])

    with op.batch_alter_table("knowledge_entries") as batch:
        batch.add_column(sa.Column("published_revision_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("draft_revision_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("lock_version", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_knowledge_published_revision", "knowledge_revisions", ["published_revision_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_knowledge_draft_revision", "knowledge_revisions", ["draft_revision_id"], ["id"]
        )
    with op.batch_alter_table("knowledge_chunks") as batch:
        batch.add_column(sa.Column("revision_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_knowledge_chunk_revision", "knowledge_revisions", ["revision_id"], ["id"])
    op.create_index("ix_knowledge_chunks_revision_id", "knowledge_chunks", ["revision_id"])

    op.create_table(
        "knowledge_import_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("source_document_versions.id"), nullable=True),
        sa.Column("state", sa.String(24), server_default="queued", nullable=False),
        sa.Column("stage", sa.String(40), server_default="queued", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_import_jobs_document_version_id", "knowledge_import_jobs", ["document_version_id"])
    op.create_index("ix_knowledge_import_jobs_state", "knowledge_import_jobs", ["state"])
    op.create_table(
        "knowledge_import_conflicts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("knowledge_import_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_entry_id", sa.Integer(), sa.ForeignKey("knowledge_entries.id"), nullable=True),
        sa.Column("current_revision_id", sa.String(36), sa.ForeignKey("knowledge_revisions.id"), nullable=True),
        sa.Column("incoming_revision_id", sa.String(36), sa.ForeignKey("knowledge_revisions.id"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("state", sa.String(24), server_default="pending", nullable=False),
        sa.Column("resolution_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for index, table, column in (
        ("ix_knowledge_import_conflicts_job_id", "knowledge_import_conflicts", "job_id"),
        ("ix_knowledge_import_conflicts_knowledge_entry_id", "knowledge_import_conflicts", "knowledge_entry_id"),
        ("ix_knowledge_import_conflicts_state", "knowledge_import_conflicts", "state"),
    ):
        op.create_index(index, table, [column])

    op.create_table(
        "knowledge_publication_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("state", sa.String(24), server_default="queued", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_knowledge_publication_jobs_state", "knowledge_publication_jobs", ["state"])
    op.create_table(
        "knowledge_publication_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("knowledge_publication_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_entry_id", sa.Integer(), sa.ForeignKey("knowledge_entries.id"), nullable=False),
        sa.Column("revision_id", sa.String(36), sa.ForeignKey("knowledge_revisions.id"), nullable=False),
        sa.Column("expected_lock_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(24), server_default="queued", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("job_id", "knowledge_entry_id", name="uq_publication_entry"),
    )
    op.create_index("ix_knowledge_publication_items_job_id", "knowledge_publication_items", ["job_id"])
    op.create_index("ix_knowledge_publication_items_knowledge_entry_id", "knowledge_publication_items", ["knowledge_entry_id"])
    op.create_index("ix_knowledge_publication_items_revision_id", "knowledge_publication_items", ["revision_id"])

    op.create_table(
        "knowledge_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("epoch", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    bind = op.get_bind()
    entries = list(
        bind.execute(
            sa.text("SELECT id, title, category, content, source, aliases, metadata_json, created_at FROM knowledge_entries")
        ).mappings()
    )
    for entry in entries:
        revision_id = f"legacy_{entry['id']}"
        bind.execute(
            sa.text("""
                INSERT INTO knowledge_revisions
                    (id, knowledge_entry_id, title, category, content, source, aliases, metadata_json, created_at)
                VALUES (:id, :entry_id, :title, :category, :content, :source, :aliases, :metadata, :created_at)
            """),
            {
                "id": revision_id,
                "entry_id": entry["id"],
                "title": entry["title"],
                "category": entry["category"],
                "content": entry["content"],
                "source": entry["source"],
                "aliases": entry["aliases"],
                "metadata": entry["metadata_json"],
                "created_at": entry["created_at"],
            },
        )
        bind.execute(
            sa.text("UPDATE knowledge_entries SET published_revision_id=:revision_id, lock_version=1 WHERE id=:entry_id"),
            {"revision_id": revision_id, "entry_id": entry["id"]},
        )
        bind.execute(
            sa.text("UPDATE knowledge_chunks SET revision_id=:revision_id WHERE source_entry_id=:entry_id"),
            {"revision_id": revision_id, "entry_id": entry["id"]},
        )

    bind.execute(
        sa.text("INSERT INTO knowledge_state (id, epoch, updated_at) VALUES (1, 1, :updated_at)"),
        {"updated_at": datetime.now(UTC)},
    )
    bind.execute(sa.text("DELETE FROM qa_cache_entries"))


def downgrade() -> None:
    op.drop_table("knowledge_publication_items")
    op.drop_index("ix_knowledge_publication_jobs_state", table_name="knowledge_publication_jobs")
    op.drop_table("knowledge_publication_jobs")
    for index in (
        "ix_knowledge_import_conflicts_state",
        "ix_knowledge_import_conflicts_knowledge_entry_id",
        "ix_knowledge_import_conflicts_job_id",
    ):
        op.drop_index(index, table_name="knowledge_import_conflicts")
    op.drop_table("knowledge_import_conflicts")
    op.drop_index("ix_knowledge_import_jobs_state", table_name="knowledge_import_jobs")
    op.drop_index("ix_knowledge_import_jobs_document_version_id", table_name="knowledge_import_jobs")
    op.drop_table("knowledge_import_jobs")
    op.drop_table("knowledge_state")
    op.drop_index("ix_knowledge_chunks_revision_id", table_name="knowledge_chunks")
    with op.batch_alter_table("knowledge_chunks") as batch:
        batch.drop_column("revision_id")
    with op.batch_alter_table("knowledge_entries") as batch:
        batch.drop_column("withdrawn_at")
        batch.drop_column("lock_version")
        batch.drop_column("draft_revision_id")
        batch.drop_column("published_revision_id")
    for index in (
        "ix_knowledge_revisions_content_hash",
        "ix_knowledge_revisions_source_document_version_id",
        "ix_knowledge_revisions_base_revision_id",
        "ix_knowledge_revisions_knowledge_entry_id",
    ):
        op.drop_index(index, table_name="knowledge_revisions")
    op.drop_table("knowledge_revisions")
    op.drop_index("ix_source_document_versions_parse_status", table_name="source_document_versions")
    op.drop_index("ix_source_document_versions_document_id", table_name="source_document_versions")
    op.drop_table("source_document_versions")
    op.drop_table("source_documents")
