"""add chat speech metadata

Revision ID: c3b7e1d9a62f
Revises: a1c7f2d9b4e0
Create Date: 2026-10-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3b7e1d9a62f"
down_revision: Union[str, None] = "a1c7f2d9b4e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_logs", sa.Column("speech_metadata", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_logs", "speech_metadata")
