"""Add GuideLoop pilot observation inbox.

Revision ID: 78e2f41a6c90
Revises: ef215e4b1a10
Create Date: 2026-11-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "78e2f41a6c90"
down_revision: Union[str, None] = "ef215e4b1a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guide_loop_cases",
        sa.Column("cluster_id", sa.String(length=100), primary_key=True),
        sa.Column("category", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_guide_loop_cases_status", "guide_loop_cases", ["status"])
    op.create_table(
        "guide_loop_observations",
        sa.Column("event_id", sa.String(length=100), primary_key=True),
        sa.Column("cluster_id", sa.String(length=100), sa.ForeignKey("guide_loop_cases.cluster_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_key", sa.String(length=100), nullable=False),
        sa.Column("text", sa.String(length=280), nullable=False),
        sa.Column("poi_id", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("unit_id", sa.String(length=100), nullable=True),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("result_code", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("replay_id", sa.String(length=100), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_guide_loop_observations_cluster_created", "guide_loop_observations", ["cluster_id", "created_at"])
    op.create_index("ix_guide_loop_observations_session_cluster", "guide_loop_observations", ["session_key", "cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_guide_loop_observations_session_cluster", table_name="guide_loop_observations")
    op.drop_index("ix_guide_loop_observations_cluster_created", table_name="guide_loop_observations")
    op.drop_table("guide_loop_observations")
    op.drop_index("ix_guide_loop_cases_status", table_name="guide_loop_cases")
    op.drop_table("guide_loop_cases")
