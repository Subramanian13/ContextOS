from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db_models import HistoricalIncidentRecord
from app.historical import HistoricalIncident, RetrievedIncident


class PostgresIncidentRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def all(self) -> list[HistoricalIncident]:
        with self.sessions() as session:
            records = session.scalars(select(HistoricalIncidentRecord)).all()
        return [self._domain(record) for record in records]

    def has_embeddings(self, model: str, dimensions: int) -> bool:
        with self.sessions() as session:
            count = session.scalar(
                select(func.count())
                .select_from(HistoricalIncidentRecord)
                .where(
                    HistoricalIncidentRecord.embedding.is_not(None),
                    HistoricalIncidentRecord.embedding_model == model,
                    HistoricalIncidentRecord.embedding_dimensions == dimensions,
                )
            )
        return bool(count)

    def similarity_search(
        self,
        embedding: list[float],
        *,
        model: str,
        dimensions: int,
        limit: int = 5,
        project_category: str | None = None,
    ) -> list[RetrievedIncident]:
        distance = HistoricalIncidentRecord.embedding.cosine_distance(embedding)
        statement = select(HistoricalIncidentRecord, distance.label("distance")).where(
            HistoricalIncidentRecord.embedding.is_not(None),
            HistoricalIncidentRecord.embedding_model == model,
            HistoricalIncidentRecord.embedding_dimensions == dimensions,
        )
        if project_category:
            statement = statement.where(
                HistoricalIncidentRecord.project_category == project_category
            )
        with self.sessions() as session:
            rows = session.execute(
                statement.order_by(distance, HistoricalIncidentRecord.id).limit(limit)
            ).all()
        return [
            RetrievedIncident(self._domain(record), round(1.0 - float(value), 6))
            for record, value in rows
        ]

    @staticmethod
    def _domain(record: HistoricalIncidentRecord) -> HistoricalIncident:
        return HistoricalIncident(
            id=record.id,
            project_id=record.project_id,
            project_category=record.project_category,
            problem_description=record.problem_description,
            root_cause=record.root_cause,
            resolution=record.resolution,
            outcome=record.outcome,
            technologies=tuple(record.technologies),
            evidence_source=record.evidence_source,
            event_date=record.event_date,
        )


class PostgresHistoricalContextService:
    def __init__(self, repository: PostgresIncidentRepository, embeddings) -> None:
        self.repository = repository
        self.embeddings = embeddings

    def retrieve(
        self, query: str, limit: int = 5, project_category: str | None = None
    ) -> list[RetrievedIncident]:
        if not self.repository.has_embeddings(
            self.embeddings.model, self.embeddings.dimensions
        ):
            raise RuntimeError(
                "The OpenAI historical index is empty. Run "
                "`uv run python -m app.seed_historical` from the backend directory."
            )
        return self.repository.similarity_search(
            self.embeddings.embed_query(query),
            model=self.embeddings.model,
            dimensions=self.embeddings.dimensions,
            limit=limit,
            project_category=project_category,
        )

