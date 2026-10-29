"""add tour session operation events"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9f4c2b8016a"
down_revision: Union[str, None] = "d7c4a81e5f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tour_session_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tour_session_events_session_id", "tour_session_events", ["session_id"])
    op.create_index("ix_tour_session_events_event_type", "tour_session_events", ["event_type"])
    op.create_index("ix_tour_session_events_created_at", "tour_session_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("tour_session_events")
