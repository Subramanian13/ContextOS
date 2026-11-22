"""Persist project-to-Salesforce Account mappings and CRM snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0008_salesforce_project_mapping"
down_revision = "0007_salesforce_pkce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salesforce_project_mappings",
        sa.Column("project_id", sa.String(80), primary_key=True),
        sa.Column("connection_id", sa.String(80), nullable=False),
        sa.Column("organization_id", sa.String(80), nullable=False),
        sa.Column("account_id", sa.String(18), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("account_snapshot", sa.JSON(), nullable=True),
        sa.Column("contacts_snapshot", sa.JSON(), nullable=True),
        sa.Column("last_successful_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["salesforce_connections.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_salesforce_project_mappings_organization_id", "salesforce_project_mappings", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_salesforce_project_mappings_organization_id", table_name="salesforce_project_mappings")
    op.drop_table("salesforce_project_mappings")
