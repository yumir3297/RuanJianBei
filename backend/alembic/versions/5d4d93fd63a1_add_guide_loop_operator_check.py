"""Record an operator's live-check result separately from routing status.

Revision ID: 5d4d93fd63a1
Revises: b8f31e7206c4
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5d4d93fd63a1"
down_revision: Union[str, None] = "b8f31e7206c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guide_loop_checks", sa.Column("operator_passed", sa.Boolean(), nullable=True))
    op.add_column("guide_loop_checks", sa.Column("operator_confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("guide_loop_checks", "operator_confirmed_at")
    op.drop_column("guide_loop_checks", "operator_passed")
