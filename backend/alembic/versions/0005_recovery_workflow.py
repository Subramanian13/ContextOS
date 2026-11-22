"""Add controlled recovery proposal, execution state, and structured audit history."""
from alembic import op
import sqlalchemy as sa

revision = "0005_recovery_workflow"
down_revision = "0004_legacy_embedding_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_proposals",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(80), nullable=False, index=True),
        sa.Column("project_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("proposed_changes", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("scenario_assumptions", sa.JSON(), nullable=False),
        sa.Column("unblock_dates", sa.JSON(), nullable=False),
        sa.Column("customer_followups", sa.JSON(), nullable=False),
        sa.Column("simulation_results", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("approver_identity", sa.String(160)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("execution_result", sa.JSON()),
        sa.Column("idempotency_key", sa.String(160), unique=True),
    )
    op.create_table(
        "project_execution_states",
        sa.Column("project_id", sa.String(80), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("task_changes", sa.JSON(), nullable=False),
        sa.Column("customer_followups", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, type_ in (
        ("project_id", sa.String(80)), ("proposal_id", sa.String(100)),
        ("actor", sa.String(160)), ("action", sa.String(100)),
        ("before_state", sa.JSON()), ("after_state", sa.JSON()),
        ("execution_result", sa.JSON()),
    ):
        op.add_column("audit_events", sa.Column(name, type_, nullable=True))
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.create_index("ix_audit_events_proposal_id", "audit_events", ["proposal_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_proposal_id", table_name="audit_events")
    op.drop_index("ix_audit_events_project_id", table_name="audit_events")
    for name in ("execution_result", "after_state", "before_state", "action", "actor", "proposal_id", "project_id"):
        op.drop_column("audit_events", name)
    op.drop_table("project_execution_states")
    op.drop_table("recovery_proposals")
