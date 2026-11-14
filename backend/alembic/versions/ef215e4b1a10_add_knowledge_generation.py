"""Track knowledge and vector index generations.

Revision ID: ef215e4b1a10
Revises: c3b7e1d9a62f
Create Date: 2026-11-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef215e4b1a10"
down_revision: Union[str, None] = "c3b7e1d9a62f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("indexed_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        sa.text(
            "INSERT INTO knowledge_generations (id, generation, indexed_generation, updated_at) "
            "VALUES (1, 1, 0, CURRENT_TIMESTAMP)"
        )
    )


def downgrade() -> None:
    op.drop_table("knowledge_generations")
