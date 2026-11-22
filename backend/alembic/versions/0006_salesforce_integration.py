"""Add encrypted Salesforce connection and one-time OAuth state records."""
from alembic import op
import sqlalchemy as sa

revision = "0006_salesforce_integration"
down_revision = "0005_recovery_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "salesforce_oauth_states",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_salesforce_oauth_states_expires_at", "salesforce_oauth_states", ["expires_at"])
    op.create_table(
        "salesforce_connections",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("instance_url", sa.String(500), nullable=False),
        sa.Column("organization_id", sa.String(80)),
        sa.Column("organization_name", sa.String(240)),
        sa.Column("organization_type", sa.String(120)),
        sa.Column("user_id", sa.String(80)),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("available_objects", sa.JSON(), nullable=False),
        sa.Column("object_permissions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(240)),
    )
    op.create_index("ix_salesforce_connections_status", "salesforce_connections", ["status"])


def downgrade() -> None:
    op.drop_index("ix_salesforce_connections_status", table_name="salesforce_connections")
    op.drop_table("salesforce_connections")
    op.drop_index("ix_salesforce_oauth_states_expires_at", table_name="salesforce_oauth_states")
    op.drop_table("salesforce_oauth_states")
