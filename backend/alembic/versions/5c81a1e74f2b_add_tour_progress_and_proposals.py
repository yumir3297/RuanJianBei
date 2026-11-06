"""add persisted tour progress and proposals

Revision ID: 5c81a1e74f2b
Revises: f324abc9d012
Create Date: 2026-10-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "5c81a1e74f2b"
down_revision: Union[str, Sequence[str], None] = "f324abc9d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tour_progress",
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("progress_version", sa.Integer(), nullable=False),
        sa.Column("progress_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_table(
        "tour_progress_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("stop_id", sa.String(36), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "version", name="uq_tour_progress_event_session_version"),
    )
    op.create_index("ix_tour_progress_events_session_id", "tour_progress_events", ["session_id"])
    op.create_index("ix_tour_progress_events_created_at", "tour_progress_events", ["created_at"])
    op.create_table(
        "itinerary_proposals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("progress_version", sa.Integer(), nullable=False),
        sa.Column("draft_digest", sa.String(64), nullable=False),
        sa.Column("catalog_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("operations_json", sa.Text(), nullable=False),
        sa.Column("candidate_json", sa.Text(), nullable=False),
        sa.Column("diff_json", sa.Text(), nullable=False),
        sa.Column("validation_json", sa.Text(), nullable=False),
        sa.Column("clarification", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_revision_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["tour_identities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("owner_id", "session_id", "expires_at"):
        op.create_index(f"ix_itinerary_proposals_{column}", "itinerary_proposals", [column])


def downgrade() -> None:
    for column in ("expires_at", "session_id", "owner_id"):
        op.drop_index(f"ix_itinerary_proposals_{column}", table_name="itinerary_proposals")
    op.drop_table("itinerary_proposals")
    op.drop_index("ix_tour_progress_events_created_at", table_name="tour_progress_events")
    op.drop_index("ix_tour_progress_events_session_id", table_name="tour_progress_events")
    op.drop_table("tour_progress_events")
    op.drop_table("tour_progress")
