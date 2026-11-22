"""Add encrypted PKCE verifier to Salesforce OAuth state."""
from alembic import op
import sqlalchemy as sa

revision = "0007_salesforce_pkce"
down_revision = "0006_salesforce_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("salesforce_oauth_states", sa.Column("encrypted_code_verifier", sa.Text(), nullable=True))
    op.execute("DELETE FROM salesforce_oauth_states")
    op.alter_column("salesforce_oauth_states", "encrypted_code_verifier", nullable=False)


def downgrade() -> None:
    op.drop_column("salesforce_oauth_states", "encrypted_code_verifier")
