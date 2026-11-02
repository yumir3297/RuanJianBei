"""Stop upgrades of known incomplete W02 histories; does not repair them."""

from alembic import context, op
import sqlalchemy as sa

revision = "7d2e93a5b601"
down_revision = "6e1a4c7d9b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Legacy W02 schema check requires an online schema inspection")
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    required_tables = {"tour_progress", "tour_progress_events", "itinerary_proposals", "knowledge_revisions"}
    missing = sorted(required_tables - tables)
    if "itinerary_proposals" in tables:
        columns = {column["name"] for column in inspector.get_columns("itinerary_proposals")}
        missing.extend(f"itinerary_proposals.{name}" for name in sorted({"base_snapshot_json", "execution_job_id"} - columns))
    if missing:
        raise RuntimeError(
            "incomplete legacy W02 schema: " + ", ".join(missing)
            + "; back up and inspect a database copy before selecting a repair migration"
        )


def downgrade() -> None:
    pass
