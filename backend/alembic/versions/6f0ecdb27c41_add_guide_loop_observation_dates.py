"""Persist query dates and clarify-only observation siblings.

Revision ID: 6f0ecdb27c41
Revises: 5d4d93fd63a1
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6f0ecdb27c41"
down_revision: Union[str, None] = "5d4d93fd63a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guide_loop_observations", sa.Column("requested_cluster_id", sa.String(100), nullable=True))
    op.add_column("guide_loop_observations", sa.Column("queried_date", sa.Date(), nullable=True))
    op.add_column("guide_loop_observations", sa.Column("match_decision", sa.String(30), nullable=True))
    op.add_column("guide_loop_observations", sa.Column("reason_code", sa.String(64), nullable=True))
    op.execute("UPDATE guide_loop_observations SET requested_cluster_id = cluster_id WHERE requested_cluster_id IS NULL")


def downgrade() -> None:
    op.drop_column("guide_loop_observations", "reason_code")
    op.drop_column("guide_loop_observations", "match_decision")
    op.drop_column("guide_loop_observations", "queried_date")
    op.drop_column("guide_loop_observations", "requested_cluster_id")
