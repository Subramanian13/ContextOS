"""Add isolated OpenAI embedding collection and preserve legacy vectors."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0003_openai_embeddings"
down_revision = "0002_historical_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_historical_incidents_embedding_hnsw", table_name="historical_incidents")
    op.alter_column("historical_incidents", "embedding", new_column_name="embedding_legacy")
    op.alter_column("historical_incidents", "embedding_legacy", nullable=True)
    op.add_column("historical_incidents", sa.Column("embedding", Vector(1536), nullable=True))
    op.add_column("historical_incidents", sa.Column("embedding_model", sa.String(160), nullable=True))
    op.add_column("historical_incidents", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.add_column("historical_incidents", sa.Column("embedding_content_hash", sa.String(64), nullable=True))
    op.add_column("historical_incidents", sa.Column("embedding_tokens", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE historical_incidents SET embedding_model = 'legacy-gemini-or-deterministic', "
        "embedding_dimensions = 768 WHERE embedding_legacy IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_historical_incidents_openai_embedding_hnsw "
        "ON historical_incidents USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_historical_incidents_openai_embedding_hnsw", table_name="historical_incidents")
    op.drop_column("historical_incidents", "embedding_tokens")
    op.drop_column("historical_incidents", "embedding_content_hash")
    op.drop_column("historical_incidents", "embedding_dimensions")
    op.drop_column("historical_incidents", "embedding_model")
    op.drop_column("historical_incidents", "embedding")
    op.alter_column("historical_incidents", "embedding_legacy", nullable=False)
    op.alter_column("historical_incidents", "embedding_legacy", new_column_name="embedding")
    op.execute(
        "CREATE INDEX ix_historical_incidents_embedding_hnsw "
        "ON historical_incidents USING hnsw (embedding vector_cosine_ops)"
    )
