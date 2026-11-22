from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.db_models import AuditEventRecord, ProjectExecutionStateRecord, RecoveryProposalRecord
from app.domain.scheduler import ScheduleValidationError
from app.schemas import ProposalCreateRequest, ProposalDecisionRequest, ProposalExecuteRequest, TaskChangeRequest
from app.seed import ACME, VERTEX
from app.workflow import ProposalStatus, RecoveryWorkflowService, WorkflowError


@pytest.fixture
def sessions():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[RecoveryProposalRecord.__table__, ProjectExecutionStateRecord.__table__, AuditEventRecord.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def proposal_request(**overrides):
    values = dict(
        title="Parallel Salesforce sandbox validation",
        unblock_dates={"acme-api-credentials": date(2026, 11, 23)},
        task_changes=[TaskChangeRequest(task_id="acme-sandbox-validation", resource_id="eng")],
        evidence_references=["INC-001"],
        assumptions=["Credential availability is hypothetical."],
        customer_followups=["Demo operator follows up with Acme security operations."],
    )
    values.update(overrides)
    return ProposalCreateRequest(**values)


def approved(service):
    item = service.create(ACME, proposal_request())
    service.submit(item.id)
    return service.approve(item.id, ProposalDecisionRequest(actor="Demo operator"))


def test_approval_is_required_and_rejection_prevents_execution(sessions) -> None:
    service = RecoveryWorkflowService(sessions)
    item = service.create(ACME, proposal_request())
    with pytest.raises(WorkflowError, match="approved"):
        service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-0001"))
    service.submit(item.id)
    rejected = service.reject(item.id, ProposalDecisionRequest(actor="Demo operator", reason="Not accepted"))
    assert rejected.status == ProposalStatus.REJECTED
    with pytest.raises(WorkflowError, match="approved"):
        service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-0002"))


def test_execution_is_idempotent_increments_version_and_preserves_blocker(sessions) -> None:
    service = RecoveryWorkflowService(sessions)
    item = approved(service)
    request = ProposalExecuteRequest(actor="Demo operator", idempotency_key="execute-acme-001")
    first = service.execute(ACME, item.id, request)
    second = service.execute(ACME, item.id, request)
    assert first.status == ProposalStatus.EXECUTED
    assert second.execution_result == first.execution_result
    assert first.execution_result["project_version"] == 2
    assert first.execution_result["actual_schedule"]["forecast_status"] == "unresolved"
    assert first.execution_result["conditional_schedule"]["forecast_completion"] == "2026-12-02"
    assert first.execution_result["remaining_blockers"] == ["acme-api-credentials"]
    assert ACME.blockers[0].condition_satisfied is False
    with pytest.raises(WorkflowError, match="already been executed"):
        service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-acme-002"))
    updated = service.project_state(ACME)
    assert updated.version == 2
    assert next(task for task in updated.tasks if task.id == "acme-sandbox-validation").resource_id == "eng"
    assert any(event.action == "proposal_executed" for event in service.audit_history(ACME.id))


def test_stale_proposal_is_rejected_and_audited(sessions) -> None:
    service = RecoveryWorkflowService(sessions)
    item = approved(service)
    with sessions.begin() as session:
        session.add(ProjectExecutionStateRecord(project_id=ACME.id, version=2, task_changes=[], customer_followups=[], updated_at=datetime.now(timezone.utc)))
    stale = service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-stale-1"))
    assert stale.status == ProposalStatus.STALE
    assert any(event.action == "proposal_stale" for event in service.audit_history(ACME.id))


def test_stale_proposal_cannot_be_approved(sessions) -> None:
    service=RecoveryWorkflowService(sessions)
    item=service.create(ACME,proposal_request()); service.submit(item.id)
    stale=service.approve(item.id,ProposalDecisionRequest(actor="Demo operator"),current_project_version=2)
    assert stale.status==ProposalStatus.STALE
    assert any(event.action=="proposal_stale" for event in service.audit_history(ACME.id))


def test_identical_active_proposal_is_not_duplicated(sessions) -> None:
    service=RecoveryWorkflowService(sessions)
    service.create(ACME,proposal_request())
    with pytest.raises(WorkflowError,match="identical active"):
        service.create(ACME,proposal_request())


def test_execution_marks_other_active_versions_stale(sessions) -> None:
    service=RecoveryWorkflowService(sessions)
    winner=approved(service)
    other=service.create(ACME,proposal_request(title="Alternative supported recovery",task_changes=[TaskChangeRequest(task_id="acme-security-review",resource_id="qa")]))
    service.submit(other.id)
    service.execute(ACME,winner.id,ProposalExecuteRequest(idempotency_key="execute-stale-others"))
    assert service.get(other.id).status==ProposalStatus.STALE


def test_invalid_resource_and_dependency_changes_are_rejected_before_persistence(sessions) -> None:
    service = RecoveryWorkflowService(sessions)
    with pytest.raises(ScheduleValidationError, match="not qualified"):
        service.create(ACME, proposal_request(task_changes=[TaskChangeRequest(task_id="acme-api-build", resource_id="impl")]))
    with pytest.raises(ScheduleValidationError, match="cannot remove required"):
        service.create(ACME, proposal_request(task_changes=[TaskChangeRequest(task_id="acme-go-live", predecessor_ids=[])]))


def test_transaction_rolls_back_state_proposal_and_audit_on_failure(sessions) -> None:
    setup = RecoveryWorkflowService(sessions)
    item = approved(setup)
    service = RecoveryWorkflowService(sessions, failure_injector=lambda: (_ for _ in ()).throw(RuntimeError("forced failure")))
    with pytest.raises(RuntimeError, match="forced failure"):
        service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-rollback"))
    with sessions() as session:
        assert session.get(ProjectExecutionStateRecord, ACME.id) is None
        stored = session.get(RecoveryProposalRecord, item.id)
        assert stored.status == ProposalStatus.APPROVED
        assert stored.idempotency_key is None
        actions = list(session.scalars(select(AuditEventRecord.action)))
        assert "proposal_executed" not in actions


def test_synthetic_demo_reset_is_scoped_and_reproducible(sessions) -> None:
    service = RecoveryWorkflowService(sessions)
    item = approved(service)
    service.execute(ACME, item.id, ProposalExecuteRequest(idempotency_key="execute-before-reset"))
    result = service.reset_demo_project(ACME.id)
    assert result == {"proposals_removed": 1, "audit_events_removed": 4, "project_state_reset": 1}
    assert service.project_state(ACME).version == 1
    assert service.list(ACME.id) == []
    assert service.audit_history(ACME.id) == []


def test_new_project_recovery_executes_in_isolation_and_is_audited(sessions) -> None:
    service=RecoveryWorkflowService(sessions)
    request=ProposalCreateRequest(
        title="Qualified engineer reassignment",
        task_changes=[TaskChangeRequest(task_id="vf-connector",resource_id="backup-eng",duration_days=6)],
        evidence_references=["INC-017"],
        assumptions=["One working day of handoff overhead is retained."],
    )
    item=service.create(VERTEX,request)
    service.submit(item.id)
    service.approve(item.id,ProposalDecisionRequest(actor="Demo operator"))
    executed=service.execute(VERTEX,item.id,ProposalExecuteRequest(idempotency_key="execute-vertex-001"))
    assert executed.status==ProposalStatus.EXECUTED
    assert service.project_state(VERTEX).version==2
    changed=next(task for task in service.project_state(VERTEX).tasks if task.id=="vf-connector")
    assert changed.resource_id=="backup-eng" and changed.duration_days==6
    assert service.project_state(ACME).version==1
    assert any(event.action=="proposal_executed" for event in service.audit_history(VERTEX.id))
