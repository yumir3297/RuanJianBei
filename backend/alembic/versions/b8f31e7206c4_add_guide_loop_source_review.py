"""Persist operator source-review attestation on GuideLoop revisions.

Revision ID: b8f31e7206c4
Revises: 901bf4c2da73
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8f31e7206c4"
down_revision: Union[str, None] = "901bf4c2da73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guide_loop_revisions", sa.Column("source_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("guide_loop_revisions", sa.Column("source_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("guide_loop_revisions", "source_reviewed_at")
    op.drop_column("guide_loop_revisions", "source_reviewed")
