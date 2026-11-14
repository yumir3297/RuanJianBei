"""Record optional K01 references without inventing links for legacy revisions."""
from alembic import op
import sqlalchemy as sa

revision = "c2a8e17f5b40"
down_revision = "bd17a3f492c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("guide_loop_revisions", sa.Column("knowledge_entry_id", sa.Integer(), nullable=True))
    op.add_column("guide_loop_revisions", sa.Column("knowledge_revision_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("guide_loop_revisions", "knowledge_revision_id")
    op.drop_column("guide_loop_revisions", "knowledge_entry_id")
