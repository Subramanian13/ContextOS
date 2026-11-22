"""Add pgvector historical incident evidence."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_historical_incidents"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "historical_incidents",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("project_category", sa.String(120), nullable=False),
        sa.Column("problem_description", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("technologies", sa.JSON(), nullable=False),
        sa.Column("evidence_source", sa.String(240), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
    )
    op.create_index("ix_historical_incidents_project_id", "historical_incidents", ["project_id"])
    op.create_index("ix_historical_incidents_category", "historical_incidents", ["project_category"])
    op.execute(
        "CREATE INDEX ix_historical_incidents_embedding_hnsw "
        "ON historical_incidents USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("historical_incidents")

