from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy.orm import sessionmaker

from app.db import create_database_engine
from app.historical import (
    DEFAULT_CONTEXT_SERVICE,
)
from app.ai import OpenAIEmbeddingProvider
from app.historical_repository import (
    PostgresHistoricalContextService,
    PostgresIncidentRepository,
)


@lru_cache(maxsize=1)
def configured_context_service():
    if os.getenv("HISTORICAL_STORE", "memory").lower() != "postgres":
        return DEFAULT_CONTEXT_SERVICE
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required when HISTORICAL_STORE=postgres"
        )
    dimensions = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
    if dimensions != 1536:
        raise RuntimeError(
            "OPENAI_EMBEDDING_DIMENSIONS must be 1536 for the current pgvector schema"
        )
    embeddings = OpenAIEmbeddingProvider(
        api_key,
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        dimensions,
        timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "1")),
    )
    sessions = sessionmaker(bind=create_database_engine(), expire_on_commit=False)
    return PostgresHistoricalContextService(PostgresIncidentRepository(sessions), embeddings)
