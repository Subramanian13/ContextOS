"""Initial project scheduling schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("projects", sa.Column("id", sa.String(80), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("customer", sa.String(160), nullable=False), sa.Column("project_type", sa.String(120), nullable=False), sa.Column("start_date", sa.Date(), nullable=False), sa.Column("deadline", sa.Date(), nullable=False), sa.Column("version", sa.Integer(), nullable=False))
    op.create_table("resources", sa.Column("id", sa.String(80), primary_key=True), sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("available_from", sa.Date(), nullable=False))
    op.create_table("blockers", sa.Column("id", sa.String(100), primary_key=True), sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("condition_satisfied", sa.Boolean(), nullable=False), sa.Column("satisfied_on", sa.Date(), nullable=True))
    op.create_table("tasks", sa.Column("id", sa.String(100), primary_key=True), sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("duration_days", sa.Integer(), nullable=False), sa.Column("resource_id", sa.String(80), sa.ForeignKey("resources.id"), nullable=True), sa.Column("blocker_id", sa.String(100), sa.ForeignKey("blockers.id"), nullable=True), sa.Column("milestone", sa.String(100), nullable=True), sa.CheckConstraint("duration_days >= 1", name="ck_task_duration_positive"))
    op.create_table("task_dependencies", sa.Column("task_id", sa.String(100), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True), sa.Column("predecessor_id", sa.String(100), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True), sa.CheckConstraint("task_id <> predecessor_id", name="ck_dependency_not_self"))
    op.create_table("project_events", sa.Column("id", sa.String(100), primary_key=True), sa.Column("project_id", sa.String(80), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("kind", sa.String(80), nullable=False), sa.Column("summary", sa.Text(), nullable=False))
    op.create_table("audit_events", sa.Column("id", sa.String(100), primary_key=True), sa.Column("aggregate_id", sa.String(100), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("event_type", sa.String(100), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("aggregate_id", "sequence", name="uq_audit_sequence"))


def downgrade() -> None:
    for table in ("audit_events", "project_events", "task_dependencies", "tasks", "blockers", "resources", "projects"):
        op.drop_table(table)

