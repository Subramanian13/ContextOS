from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ProjectRecord(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    customer: Mapped[str] = mapped_column(String(160))
    project_type: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date)
    deadline: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)
    tasks: Mapped[list["TaskRecord"]] = relationship(cascade="all, delete-orphan")


class ResourceRecord(Base):
    __tablename__ = "resources"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    available_from: Mapped[date] = mapped_column(Date)


class BlockerRecord(Base):
    __tablename__ = "blockers"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text)
    condition_satisfied: Mapped[bool] = mapped_column(Boolean, default=False)
    satisfied_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class TaskRecord(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    duration_days: Mapped[int] = mapped_column(Integer)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"), nullable=True)
    blocker_id: Mapped[str | None] = mapped_column(ForeignKey("blockers.id"), nullable=True)
    milestone: Mapped[str | None] = mapped_column(String(100), nullable=True)


class DependencyRecord(Base):
    __tablename__ = "task_dependencies"
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    predecessor_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)


class ProjectEventRecord(Base):
    __tablename__ = "project_events"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("aggregate_id", "sequence", name="uq_audit_sequence"),)
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    aggregate_id: Mapped[str] = mapped_column(String(100), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    project_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    proposal_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    actor: Mapped[str | None] = mapped_column(String(160), nullable=True)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RecoveryProposalRecord(Base):
    __tablename__ = "recovery_proposals"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(80), index=True)
    project_version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    proposed_changes: Mapped[list[dict]] = mapped_column(JSON)
    evidence_references: Mapped[list[str]] = mapped_column(JSON)
    scenario_assumptions: Mapped[list[str]] = mapped_column(JSON)
    unblock_dates: Mapped[dict[str, str]] = mapped_column(JSON)
    customer_followups: Mapped[list[str]] = mapped_column(JSON)
    simulation_results: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approver_identity: Mapped[str | None] = mapped_column(String(160), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True)


class ProjectExecutionStateRecord(Base):
    __tablename__ = "project_execution_states"
    project_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    task_changes: Mapped[list[dict]] = mapped_column(JSON)
    customer_followups: Mapped[list[str]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SalesforceOAuthStateRecord(Base):
    __tablename__ = "salesforce_oauth_states"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    encrypted_code_verifier: Mapped[str] = mapped_column(Text)


class SalesforceConnectionRecord(Base):
    __tablename__ = "salesforce_connections"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    instance_url: Mapped[str] = mapped_column(String(500))
    organization_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    organization_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(JSON)
    available_objects: Mapped[list[str]] = mapped_column(JSON)
    object_permissions: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), index=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)


class SalesforceProjectMappingRecord(Base):
    __tablename__ = "salesforce_project_mappings"
    project_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    connection_id: Mapped[str] = mapped_column(String(80), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(18), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    account_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contacts_snapshot: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    last_successful_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HistoricalIncidentRecord(Base):
    __tablename__ = "historical_incidents"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    project_category: Mapped[str] = mapped_column(String(120), index=True)
    problem_description: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(JSON)
    evidence_source: Mapped[str] = mapped_column(String(240))
    event_date: Mapped[date] = mapped_column(Date)
    embedding_legacy: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

