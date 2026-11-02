"""Detect known missing knowledge workspace structures after partial upgrades."""

from alembic import context, op
import sqlalchemy as sa

revision = "91a0c5e2f347"
down_revision = "7d2e93a5b601"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Knowledge workspace check requires an online schema inspection")
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    required_tables = {
        "source_documents", "source_document_versions", "knowledge_revisions",
        "knowledge_import_jobs", "knowledge_import_conflicts", "knowledge_import_batches",
        "knowledge_publication_jobs", "knowledge_publication_items", "knowledge_state",
    }
    missing = sorted(required_tables - tables)
    required_columns = {
        "knowledge_entries": {"published_revision_id", "draft_revision_id", "lock_version", "withdrawn_at"},
        "knowledge_chunks": {"revision_id"},
        "knowledge_import_jobs": {"batch_id", "original_filename", "item_index"},
    }
    for table, required in required_columns.items():
        if table not in tables:
            if table not in missing:
                missing.append(table)
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        missing.extend(f"{table}.{name}" for name in sorted(required - columns))
    if missing:
        raise RuntimeError(
            "incomplete knowledge workspace schema: " + ", ".join(missing)
            + "; back up and inspect a database copy before selecting a repair migration"
        )


def downgrade() -> None:
    pass
