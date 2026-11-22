from __future__ import annotations

import os

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import config as _config  # noqa: F401
from app.ai import OpenAIEmbeddingProvider, content_hash
from app.db import create_database_engine
from app.db_models import HistoricalIncidentRecord
from app.historical import INCIDENTS


def embedding_is_stale(record, incident, model: str, dimensions: int) -> bool:
    return (
        record is None
        or record.embedding is None
        or record.embedding_model != model
        or record.embedding_dimensions != dimensions
        or record.embedding_content_hash != content_hash(incident.search_text)
    )


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is required to index PostgreSQL historical evidence."
        )
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dimensions = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
    if dimensions != 1536:
        raise SystemExit(
            "OPENAI_EMBEDDING_DIMENSIONS must be 1536 for the current pgvector schema."
        )
    provider = OpenAIEmbeddingProvider(
        api_key,
        model,
        dimensions,
        timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "1")),
    )
    engine = create_database_engine()
    with Session(engine) as session, session.begin():
        existing = {
            record.id: record
            for record in session.query(HistoricalIncidentRecord).all()
        }
        stale = [
            incident
            for incident in INCIDENTS
            if embedding_is_stale(existing.get(incident.id), incident, model, dimensions)
        ]
        vectors = provider.embed_many([incident.search_text for incident in stale]) if stale else []
        vector_by_id = {
            incident.id: vector for incident, vector in zip(stale, vectors, strict=True)
        }
        for incident in INCIDENTS:
            values = {
                "id": incident.id,
                "project_id": incident.project_id,
                "project_category": incident.project_category,
                "problem_description": incident.problem_description,
                "root_cause": incident.root_cause,
                "resolution": incident.resolution,
                "outcome": incident.outcome,
                "technologies": list(incident.technologies),
                "evidence_source": incident.evidence_source,
                "event_date": incident.event_date,
            }
            if incident.id in vector_by_id:
                values.update(
                    {
                        "embedding": vector_by_id[incident.id],
                        "embedding_model": model,
                        "embedding_dimensions": dimensions,
                        "embedding_content_hash": content_hash(incident.search_text),
                    }
                )
            statement = insert(HistoricalIncidentRecord).values(**values)
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[HistoricalIncidentRecord.id], set_=values
                )
            )
    print(
        f"Preserved {len(INCIDENTS)} incidents; indexed {len(stale)} with "
        f"{model} ({dimensions} dimensions); reused {len(INCIDENTS) - len(stale)} cached vectors"
    )


if __name__ == "__main__":
    try:
        main()
    except OperationalError as exc:
        raise SystemExit(
            "Could not connect to PostgreSQL. Start Docker Desktop, run "
            "`docker compose up -d db` from the repository root, and retry. "
            "For the default HISTORICAL_STORE=memory demo, do not run this seed command."
        ) from exc
