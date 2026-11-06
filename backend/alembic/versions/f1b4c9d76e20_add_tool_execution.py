"""add durable tool execution records"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1b4c9d76e20"
down_revision: Union[str, None] = "e9f4c2b8016a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("principal_type", sa.String(20), nullable=False),
        sa.Column("principal_id", sa.String(100), nullable=False),
        sa.Column("site_id", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), sa.ForeignKey("tour_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_version", sa.String(40), nullable=False),
        sa.Column("workflow_schema_version", sa.String(40), nullable=False),
        sa.Column("recovery_mode", sa.String(24), server_default="durable_resume", nullable=False),
        sa.Column("retry_safe", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("progress_version", sa.Integer(), nullable=True),
        sa.Column("content_digest", sa.String(64), nullable=True),
        sa.Column("status", sa.String(24), server_default="queued", nullable=False),
        sa.Column("reason", sa.String(80), nullable=True),
        sa.Column("progress_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(100), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fence", sa.Integer(), server_default="0", nullable=False),
        sa.Column("manual_retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tool_jobs_principal_id", "tool_jobs", ["principal_id"])
    op.create_index("ix_tool_jobs_site_id", "tool_jobs", ["site_id"])
    op.create_index("ix_tool_jobs_status", "tool_jobs", ["status"])
    op.create_index("ix_tool_jobs_deadline_at", "tool_jobs", ["deadline_at"])
    op.create_index("ix_tool_jobs_lease_until", "tool_jobs", ["lease_until"])
    op.create_index("ix_tool_jobs_claim", "tool_jobs", ["status", "next_run_at", "created_at"])
    op.create_index("ix_tool_jobs_target", "tool_jobs", ["target_type", "target_id", "status"])

    op.create_table(
        "tool_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_key", sa.String(100), nullable=False),
        sa.Column("status", sa.String(24), server_default="queued", nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False),
        sa.Column("external_state", sa.String(24), server_default="not_started", nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("job_id", "step_key", name="uq_tool_steps_job_key"),
    )
    op.create_index("ix_tool_steps_job_id", "tool_steps", ["job_id"])
    op.create_index("ix_tool_steps_job_status", "tool_steps", ["job_id", "status"])

    op.create_table(
        "tool_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(36), sa.ForeignKey("tool_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_state", sa.String(24), server_default="not_started", nullable=False),
        sa.Column("outcome", sa.String(24), nullable=True),
        sa.Column("provider_request_id", sa.String(160), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.UniqueConstraint("step_id", "attempt_number", name="uq_tool_attempt_step_number"),
    )
    op.create_index("ix_tool_attempts_job_id", "tool_attempts", ["job_id"])
    op.create_index("ix_tool_attempts_step_id", "tool_attempts", ["step_id"])

    op.create_table(
        "tool_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("summary", sa.String(240), nullable=False),
        sa.Column("payload_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("job_id", "seq", name="uq_tool_events_job_seq"),
    )
    op.create_index("ix_tool_events_job_id", "tool_events", ["job_id"])

    op.create_table(
        "tool_command_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("principal_type", sa.String(20), nullable=False),
        sa.Column("principal_id", sa.String(100), nullable=False),
        sa.Column("command", sa.String(40), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("tool_jobs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("principal_type", "principal_id", "command", "key", name="uq_tool_receipt_scope_key"),
    )
    op.create_index("ix_tool_command_receipts_job_id", "tool_command_receipts", ["job_id"])
    op.create_index("ix_tool_command_receipts_expires_at", "tool_command_receipts", ["expires_at"])


def downgrade() -> None:
    op.drop_table("tool_command_receipts")
    op.drop_table("tool_events")
    op.drop_table("tool_attempts")
    op.drop_table("tool_steps")
    op.drop_table("tool_jobs")
