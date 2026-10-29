"""Add durable knowledge import batches.

Revision ID: d12a77c0e40e
Revises: c84d0f1a7b92
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d12a77c0e40e"
down_revision: Union[str, None] = "c84d0f1a7b92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_import_batches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_import_batches_state", "knowledge_import_batches", ["state"])
    with op.batch_alter_table("knowledge_import_jobs") as batch_op:
        batch_op.add_column(sa.Column("batch_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("item_index", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key(
            "fk_knowledge_import_jobs_batch_id",
            "knowledge_import_batches",
            ["batch_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_knowledge_import_jobs_batch_id", ["batch_id"])


def downgrade() -> None:
    with op.batch_alter_table("knowledge_import_jobs") as batch_op:
        batch_op.drop_index("ix_knowledge_import_jobs_batch_id")
        batch_op.drop_constraint("fk_knowledge_import_jobs_batch_id", type_="foreignkey")
        batch_op.drop_column("item_index")
        batch_op.drop_column("original_filename")
        batch_op.drop_column("batch_id")
    op.drop_index("ix_knowledge_import_batches_state", table_name="knowledge_import_batches")
    op.drop_table("knowledge_import_batches")
