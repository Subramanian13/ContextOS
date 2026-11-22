"""Allow Salesforce mappings for seed-backed ContextOS projects."""
from alembic import op

revision = "0009_seed_project_mapping"
down_revision = "0008_salesforce_project_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("salesforce_project_mappings_project_id_fkey", "salesforce_project_mappings", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key("salesforce_project_mappings_project_id_fkey", "salesforce_project_mappings", "projects", ["project_id"], ["id"], ondelete="CASCADE")
