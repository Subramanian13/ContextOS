from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from enum import StrEnum
from functools import lru_cache
from typing import Callable
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import create_database_engine
from app.db_models import AuditEventRecord, ProjectExecutionStateRecord, RecoveryProposalRecord
from app.domain.models import Project
from app.domain.scheduler import ScheduleValidationError, calculate_schedule
from app.schemas import (
    ProposalCreateRequest,
    ProposalDecisionRequest,
    ProposalExecuteRequest,
    RecoveryScenarioRequest,
    ScheduleResponse,
    SimulationRequest,
    TaskChangeRequest,
)
from app.service import build_candidate, compare_recovery_scenario


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    STALE = "stale"


class WorkflowError(ValueError):
    pass


class ProposalNotFoundError(WorkflowError):
    pass


class RecoveryWorkflowService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        failure_injector: Callable[[], None] | None = None,
    ) -> None:
        self.sessions = sessions
        self.failure_injector = failure_injector

    def project_state(self, base: Project) -> Project:
        with self.sessions() as session:
            state = session.get(ProjectExecutionStateRecord, base.id)
            if not state:
                return base
            request = SimulationRequest(
                task_changes=[TaskChangeRequest.model_validate(item) for item in state.task_changes]
            )
            return replace(build_candidate(base, request), version=state.version)

    def create(self, project: Project, request: ProposalCreateRequest) -> RecoveryProposalRecord:
        scenario_request = RecoveryScenarioRequest(
            name=request.title,
            unblock_dates=request.unblock_dates,
            task_changes=request.task_changes,
            assumptions=request.assumptions,
        )
        comparison = compare_recovery_scenario(project, scenario_request)
        signature = self._proposal_signature(project.id, project.version, request)
        active = {ProposalStatus.DRAFT, ProposalStatus.PENDING_APPROVAL, ProposalStatus.APPROVED}
        with self.sessions() as session:
            existing = list(session.scalars(select(RecoveryProposalRecord).where(RecoveryProposalRecord.project_id == project.id, RecoveryProposalRecord.status.in_(active))))
        if any(self._record_signature(item) == signature for item in existing):
            raise WorkflowError("An identical active recovery proposal already exists")
        now = datetime.now(timezone.utc)
        record = RecoveryProposalRecord(
            id=f"rp-{uuid4().hex}", project_id=project.id, project_version=project.version,
            title=request.title,
            proposed_changes=[item.model_dump(mode="json", exclude_none=True) for item in request.task_changes],
            evidence_references=request.evidence_references,
            scenario_assumptions=request.assumptions,
            unblock_dates={key: value.isoformat() for key, value in request.unblock_dates.items()},
            customer_followups=request.customer_followups,
            simulation_results=self._comparison_json(comparison), status=ProposalStatus.DRAFT,
            created_at=now, updated_at=now,
        )
        with self.sessions.begin() as session:
            session.add(record)
            self._audit(session, project.id, record.id, "Demo operator", "proposal_created", None, {"status": record.status})
        return record

    def list(self, project_id: str) -> list[RecoveryProposalRecord]:
        with self.sessions() as session:
            return list(session.scalars(select(RecoveryProposalRecord).where(RecoveryProposalRecord.project_id == project_id).order_by(RecoveryProposalRecord.created_at.desc())))

    def list_all(self) -> list[RecoveryProposalRecord]:
        with self.sessions() as session:
            return list(session.scalars(select(RecoveryProposalRecord).order_by(RecoveryProposalRecord.created_at.desc())))

    def get(self, proposal_id: str) -> RecoveryProposalRecord:
        with self.sessions() as session:
            record = session.get(RecoveryProposalRecord, proposal_id)
            if not record:
                raise ProposalNotFoundError(proposal_id)
            return record

    def submit(self, proposal_id: str, actor: str = "Demo operator") -> RecoveryProposalRecord:
        with self.sessions.begin() as session:
            record = self._locked(session, proposal_id)
            self._transition(record, ProposalStatus.DRAFT, ProposalStatus.PENDING_APPROVAL)
            record.submitted_at = record.updated_at
            self._audit(session, record.project_id, record.id, actor, "proposal_submitted", {"status": "draft"}, {"status": record.status})
        return record

    def approve(self, proposal_id: str, request: ProposalDecisionRequest, current_project_version: int | None = None) -> RecoveryProposalRecord:
        with self.sessions.begin() as session:
            record = self._locked(session, proposal_id)
            if current_project_version is not None and record.project_version != current_project_version:
                before=record.status; record.status=ProposalStatus.STALE; record.updated_at=datetime.now(timezone.utc)
                self._audit(session, record.project_id, record.id, request.actor, "proposal_stale", {"status":before,"project_version":record.project_version}, {"status":record.status,"project_version":current_project_version})
                return record
            self._transition(record, ProposalStatus.PENDING_APPROVAL, ProposalStatus.APPROVED)
            record.approver_identity = request.actor
            record.decided_at = record.updated_at
            self._audit(session, record.project_id, record.id, request.actor, "proposal_approved", {"status": "pending_approval"}, {"status": record.status})
        return record

    def reject(self, proposal_id: str, request: ProposalDecisionRequest) -> RecoveryProposalRecord:
        with self.sessions.begin() as session:
            record = self._locked(session, proposal_id)
            self._transition(record, ProposalStatus.PENDING_APPROVAL, ProposalStatus.REJECTED)
            record.approver_identity = request.actor
            record.rejection_reason = request.reason or "Rejected by demo operator"
            record.decided_at = record.updated_at
            self._audit(session, record.project_id, record.id, request.actor, "proposal_rejected", {"status": "pending_approval"}, {"status": record.status, "reason": record.rejection_reason})
        return record

    def execute(self, base_project: Project, proposal_id: str, request: ProposalExecuteRequest) -> RecoveryProposalRecord:
        try:
            with self.sessions.begin() as session:
                record = self._locked(session, proposal_id)
                if record.status == ProposalStatus.EXECUTED:
                    if record.idempotency_key == request.idempotency_key:
                        return record
                    raise WorkflowError("Proposal has already been executed")
                if record.status != ProposalStatus.APPROVED:
                    raise WorkflowError("Only an approved proposal may be executed")
                state = session.get(ProjectExecutionStateRecord, base_project.id, with_for_update=True)
                current_version = state.version if state else base_project.version
                if current_version != record.project_version:
                    before = record.status
                    record.status = ProposalStatus.STALE
                    record.updated_at = datetime.now(timezone.utc)
                    self._audit(session, record.project_id, record.id, request.actor, "proposal_stale", {"status": before, "project_version": record.project_version}, {"status": record.status, "project_version": current_version})
                    return record
                prior_changes = state.task_changes if state else []
                merged = self._merge_changes(prior_changes, record.proposed_changes)
                candidate = build_candidate(base_project, SimulationRequest(task_changes=[TaskChangeRequest.model_validate(item) for item in merged]))
                updated = replace(candidate, version=current_version + 1)
                actual_schedule = calculate_schedule(updated)
                conditional_schedule = calculate_schedule(
                    updated,
                    unblock_dates={key: datetime.fromisoformat(value).date() for key, value in record.unblock_dates.items()},
                )
                now = datetime.now(timezone.utc)
                if state:
                    state.version = updated.version
                    state.task_changes = merged
                    state.customer_followups = list(dict.fromkeys(state.customer_followups + record.customer_followups))
                    state.updated_at = now
                else:
                    session.add(ProjectExecutionStateRecord(project_id=base_project.id, version=updated.version, task_changes=merged, customer_followups=record.customer_followups, updated_at=now))
                result = {
                    "project_version": updated.version,
                    "applied_changes": record.proposed_changes,
                    "customer_followups": record.customer_followups,
                    "remaining_blockers": [item.id for item in updated.blockers if not item.condition_satisfied],
                    "actual_schedule": ScheduleResponse.model_validate(actual_schedule).model_dump(mode="json"),
                    "conditional_schedule": ScheduleResponse.model_validate(conditional_schedule).model_dump(mode="json"),
                }
                record.status = ProposalStatus.EXECUTED
                record.executed_at = now
                record.updated_at = now
                record.idempotency_key = request.idempotency_key
                record.execution_result = result
                self._audit(session, record.project_id, record.id, request.actor, "proposal_executed", {"project_version": current_version, "task_changes": prior_changes}, {"project_version": updated.version, "task_changes": merged}, result)
                other_active=list(session.scalars(select(RecoveryProposalRecord).where(RecoveryProposalRecord.project_id==record.project_id,RecoveryProposalRecord.id!=record.id,RecoveryProposalRecord.status.in_([ProposalStatus.DRAFT,ProposalStatus.PENDING_APPROVAL,ProposalStatus.APPROVED])).with_for_update()))
                for other in other_active:
                    before_status=other.status; other.status=ProposalStatus.STALE; other.updated_at=now
                    session.flush()
                    self._audit(session,other.project_id,other.id,request.actor,"proposal_stale",{"status":before_status,"project_version":other.project_version},{"status":ProposalStatus.STALE,"project_version":updated.version})
                if self.failure_injector:
                    self.failure_injector()
            return record
        except WorkflowError:
            raise

    def audit_history(self, project_id: str) -> list[AuditEventRecord]:
        with self.sessions() as session:
            return list(session.scalars(select(AuditEventRecord).where(AuditEventRecord.project_id == project_id).order_by(AuditEventRecord.occurred_at.desc())))

    def audit_history_all(self) -> list[AuditEventRecord]:
        with self.sessions() as session:
            return list(session.scalars(select(AuditEventRecord).order_by(AuditEventRecord.occurred_at.desc())))

    def reset_demo_project(self, project_id: str) -> dict[str, int]:
        with self.sessions.begin() as session:
            audit_count = session.scalar(select(func.count()).select_from(AuditEventRecord).where(AuditEventRecord.project_id == project_id)) or 0
            proposal_count = session.scalar(select(func.count()).select_from(RecoveryProposalRecord).where(RecoveryProposalRecord.project_id == project_id)) or 0
            session.execute(delete(AuditEventRecord).where(AuditEventRecord.project_id == project_id))
            session.execute(delete(RecoveryProposalRecord).where(RecoveryProposalRecord.project_id == project_id))
            state = session.get(ProjectExecutionStateRecord, project_id)
            if state:
                session.delete(state)
        return {"proposals_removed": proposal_count, "audit_events_removed": audit_count, "project_state_reset": int(state is not None)}

    @staticmethod
    def _comparison_json(comparison: dict) -> dict:
        result = dict(comparison)
        for key in ("actual", "baseline", "proposed"):
            result[key] = ScheduleResponse.model_validate(result[key]).model_dump(mode="json")
        for key in ("baseline_resource_utilization", "proposed_resource_utilization"):
            result[key] = [item.model_dump(mode="json") for item in result[key]]
        result["feasibility"] = str(result["feasibility"])
        return result

    @staticmethod
    def _merge_changes(before: list[dict], after: list[dict]) -> list[dict]:
        merged = {item["task_id"]: dict(item) for item in before}
        for item in after:
            merged[item["task_id"]] = dict(item)
        return list(merged.values())

    @staticmethod
    def _proposal_signature(project_id: str, version: int, request: ProposalCreateRequest) -> tuple:
        changes=tuple(sorted(str(item.model_dump(mode="json",exclude_none=True)) for item in request.task_changes))
        return project_id,version,changes,tuple(sorted((key,value.isoformat()) for key,value in request.unblock_dates.items()))

    @staticmethod
    def _record_signature(record: RecoveryProposalRecord) -> tuple:
        changes=tuple(sorted(str(item) for item in record.proposed_changes))
        return record.project_id,record.project_version,changes,tuple(sorted(record.unblock_dates.items()))

    @staticmethod
    def _transition(record, expected, target) -> None:
        if record.status != expected:
            raise WorkflowError(f"Proposal must be {expected} to become {target}")
        record.status = target
        record.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _locked(session: Session, proposal_id: str) -> RecoveryProposalRecord:
        record = session.scalar(select(RecoveryProposalRecord).where(RecoveryProposalRecord.id == proposal_id).with_for_update())
        if not record:
            raise ProposalNotFoundError(proposal_id)
        return record

    @staticmethod
    def _audit(session: Session, project_id: str, proposal_id: str, actor: str, action: str, before: dict | None, after: dict | None, result: dict | None = None) -> None:
        aggregate = project_id
        sequence = (session.scalar(select(func.max(AuditEventRecord.sequence)).where(AuditEventRecord.aggregate_id == aggregate)) or 0) + 1
        session.add(AuditEventRecord(id=f"ae-{uuid4().hex}", aggregate_id=aggregate, sequence=sequence, event_type=action, payload_json="{}", occurred_at=datetime.now(timezone.utc), project_id=project_id, proposal_id=proposal_id, actor=actor, action=action, before_state=before, after_state=after, execution_result=result))


@lru_cache(maxsize=1)
def configured_workflow_service() -> RecoveryWorkflowService:
    return RecoveryWorkflowService(sessionmaker(bind=create_database_engine(), expire_on_commit=False))
