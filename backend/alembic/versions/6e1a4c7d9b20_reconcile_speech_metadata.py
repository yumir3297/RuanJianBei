"""Reconcile speech metadata omitted by the legacy W02 migration lineage.

The legacy and integrated histories used the same W02 revision with different
parents.  Do not remove this column on downgrade: it may predate this revision.
"""

from alembic import context, op
import sqlalchemy as sa

revision = "6e1a4c7d9b20"
down_revision = "f1b4c9d76e20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Speech metadata reconciliation requires an online schema inspection")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_logs")}
    if "speech_metadata" not in columns:
        op.add_column("chat_logs", sa.Column("speech_metadata", sa.Text(), nullable=True))


def downgrade() -> None:
    pass
