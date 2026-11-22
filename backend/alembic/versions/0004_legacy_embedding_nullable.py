"""Allow legacy vectors to be absent on OpenAI-indexed incident upserts."""
from alembic import op

revision = "0004_legacy_embedding_nullable"
down_revision = "0003_openai_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("historical_incidents", "embedding_legacy", nullable=True)


def downgrade() -> None:
    count = op.get_bind().exec_driver_sql(
        "SELECT count(*) FROM historical_incidents WHERE embedding_legacy IS NULL"
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Cannot restore the legacy NOT NULL constraint while records lack legacy vectors"
        )
    op.alter_column("historical_incidents", "embedding_legacy", nullable=False)
