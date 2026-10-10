"""add visitor_memories

Revision ID: a1c7f2d9b4e0
Revises: b667a1ecf225
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c7f2d9b4e0"
down_revision: Union[str, None] = "b667a1ecf225"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visitor_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("site_id", sa.String(length=64), nullable=False),
        sa.Column("visited_attractions", sa.Text(), nullable=False),
        sa.Column("preference_tags", sa.Text(), nullable=False),
        sa.Column("narration_audience", sa.String(length=20), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False),
        sa.Column("last_session_id", sa.String(length=100), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_visitor_memories_id"), "visitor_memories", ["id"], unique=False)
    op.create_index(
        op.f("ix_visitor_memories_visitor_id"), "visitor_memories", ["visitor_id"], unique=False
    )
    op.create_index(
        op.f("ix_visitor_memories_site_id"), "visitor_memories", ["site_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_visitor_memories_site_id"), table_name="visitor_memories")
    op.drop_index(op.f("ix_visitor_memories_visitor_id"), table_name="visitor_memories")
    op.drop_index(op.f("ix_visitor_memories_id"), table_name="visitor_memories")
    op.drop_table("visitor_memories")
