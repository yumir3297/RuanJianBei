"""add anonymous tour sessions and immutable revisions"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d7c4a81e5f20"
down_revision: Union[str, None] = "a1c7f2d9b4e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tour_identities",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("credential_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_digest"),
    )
    op.create_index("ix_tour_identities_credential_digest", "tour_identities", ["credential_digest"])
    op.create_index("ix_tour_identities_expires_at", "tour_identities", ["expires_at"])

    op.create_table(
        "tour_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("site_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["tour_identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tour_sessions_owner_id", "tour_sessions", ["owner_id"])
    op.create_index("ix_tour_sessions_site_id", "tour_sessions", ["site_id"])
    op.create_index("ix_tour_sessions_status", "tour_sessions", ["status"])
    op.create_index("ix_tour_sessions_deleted_at", "tour_sessions", ["deleted_at"])

    op.create_table(
        "tour_session_revisions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "version", name="uq_tour_revision_session_version"),
    )
    op.create_index("ix_tour_session_revisions_session_id", "tour_session_revisions", ["session_id"])

    op.create_table(
        "tour_artifact_references",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("revision_id", sa.String(36), nullable=True),
        sa.Column("artifact_type", sa.String(40), nullable=False),
        sa.Column("artifact_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["tour_session_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tour_artifact_references_session_id", "tour_artifact_references", ["session_id"])
    op.create_index("ix_tour_artifact_references_revision_id", "tour_artifact_references", ["revision_id"])

    op.create_table(
        "tour_session_idempotency",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("endpoint", sa.String(80), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["tour_identities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["tour_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "endpoint", "key", name="uq_tour_idempotency_owner_endpoint_key"),
    )
    op.create_index("ix_tour_session_idempotency_owner_id", "tour_session_idempotency", ["owner_id"])
    op.create_index("ix_tour_session_idempotency_session_id", "tour_session_idempotency", ["session_id"])
    op.create_index("ix_tour_session_idempotency_expires_at", "tour_session_idempotency", ["expires_at"])


def downgrade() -> None:
    op.drop_table("tour_session_idempotency")
    op.drop_table("tour_artifact_references")
    op.drop_table("tour_session_revisions")
    op.drop_table("tour_sessions")
    op.drop_table("tour_identities")
