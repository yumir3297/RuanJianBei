"""Add immutable GuideLoop revisions, active pointers, and live checks.

Revision ID: 901bf4c2da73
Revises: 78e2f41a6c90
Create Date: 2026-11-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "901bf4c2da73"
down_revision: Union[str, None] = "78e2f41a6c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guide_loop_cases", sa.Column("draft_id", sa.String(100), nullable=True))
    op.add_column("guide_loop_cases", sa.Column("draft_json", sa.Text(), nullable=True))
    op.add_column("guide_loop_cases", sa.Column("draft_hash", sa.String(64), nullable=True))
    op.add_column("guide_loop_cases", sa.Column("verification_json", sa.Text(), nullable=True))
    op.create_table(
        "guide_loop_revisions",
        sa.Column("revision_id", sa.String(100), primary_key=True),
        sa.Column("base_revision", sa.String(100), nullable=False),
        sa.Column("case_id", sa.String(100), nullable=False),
        sa.Column("poi_id", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("alias", sa.String(280), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("evidence_id", sa.String(100), nullable=False),
        sa.Column("source_ref", sa.String(500), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_guide_loop_revisions_poi_id", "guide_loop_revisions", ["poi_id"])
    op.create_index("ix_guide_loop_revisions_target_id", "guide_loop_revisions", ["target_id"])
    op.create_table(
        "guide_loop_pointers",
        sa.Column("scope_key", sa.String(180), primary_key=True),
        sa.Column("poi_id", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("revision_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_guide_loop_pointers_poi_id", "guide_loop_pointers", ["poi_id"])
    op.create_table(
        "guide_loop_checks",
        sa.Column("check_id", sa.String(100), primary_key=True),
        sa.Column("case_id", sa.String(100), nullable=False),
        sa.Column("revision_id", sa.String(100), nullable=True),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("guide_loop_checks")
    op.drop_index("ix_guide_loop_pointers_poi_id", table_name="guide_loop_pointers")
    op.drop_table("guide_loop_pointers")
    op.drop_index("ix_guide_loop_revisions_target_id", table_name="guide_loop_revisions")
    op.drop_index("ix_guide_loop_revisions_poi_id", table_name="guide_loop_revisions")
    op.drop_table("guide_loop_revisions")
    op.drop_column("guide_loop_cases", "verification_json")
    op.drop_column("guide_loop_cases", "draft_hash")
    op.drop_column("guide_loop_cases", "draft_json")
    op.drop_column("guide_loop_cases", "draft_id")
