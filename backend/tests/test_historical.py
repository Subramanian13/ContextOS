import pytest
from pydantic import ValidationError

from app.historical import DEFAULT_CONTEXT_SERVICE, INCIDENTS
from app.recovery import (
    PlannerOutputError,
    PlannerUnavailableError,
    ProposedTaskChange,
    RecoveryPlanningService,
    RecoveryProposal,
    configured_recovery_service,
)
from app.seed import ACME


class FakePlanner:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    def generate(self, system_instruction: str, prompt: str) -> RecoveryProposal:
        if self.error:
            raise self.error
        assert "Never invent completion dates" in system_instruction
        assert "UNTRUSTED_HISTORICAL_EVIDENCE" in prompt
        return RecoveryProposal.model_validate(self.payload)


def valid_payload(evidence_id: str) -> dict:
    return {
        "root_cause_explanation": "Credential approval is outside the current project control path.",
        "supporting_evidence_ids": [evidence_id],
        "recommended_actions": ["Escalate credential approval and prepare independent tests."],
        "proposed_task_changes": [],
        "required_customer_actions": ["Provide and validate production API credentials."],
        "assumptions": ["No completion date is claimed until credentials are available."],
        "risks": ["The blocker may remain unresolved."],
        "reasoning_summary": "The credential blocker gates connector and downstream test work.",
        "expected_outcome_explanation": "Independent work can continue, but go-live remains unresolved.",
    }


def test_has_twelve_traceable_incidents() -> None:
    assert len(INCIDENTS) >= 12
    assert len({incident.id for incident in INCIDENTS}) == len(INCIDENTS)
    assert all(incident.evidence_source for incident in INCIDENTS)


def test_retrieval_returns_credential_incident_for_acme() -> None:
    matches = DEFAULT_CONTEXT_SERVICE.retrieve(
        "CRM integration missing production API credentials OAuth connector", 5
    )
    assert matches[0].incident.id == "INC-001"
    assert all(-1 <= item.score <= 1 for item in matches)


def test_structured_output_and_complete_acme_analysis() -> None:
    evidence = RecoveryPlanningService(DEFAULT_CONTEXT_SERVICE, FakePlanner()).evidence_for(ACME)
    service = RecoveryPlanningService(
        DEFAULT_CONTEXT_SERVICE, FakePlanner(valid_payload(evidence[0].incident.id))
    )
    returned_evidence, proposal, baseline, projected = service.analyze(ACME)
    assert proposal.supporting_evidence_ids[0] in {item.incident.id for item in returned_evidence}
    assert baseline.forecast_status == "unresolved"
    assert projected.forecast_status == "unresolved"
    assert ACME.tasks[2].duration_days == 4


def test_evidence_id_must_have_been_retrieved() -> None:
    service = RecoveryPlanningService(DEFAULT_CONTEXT_SERVICE, FakePlanner(valid_payload("INC-999")))
    with pytest.raises(PlannerOutputError, match="not retrieved"):
        service.analyze(ACME)


def test_unsupported_recommendation_action_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProposedTaskChange(
            action="delete_task", task_id="acme-api-build", rationale="unsupported"
        )


def test_missing_openai_key_is_graceful(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(PlannerUnavailableError, match="not configured"):
        configured_recovery_service(DEFAULT_CONTEXT_SERVICE)


def test_model_failure_is_not_replaced_with_fabricated_output() -> None:
    service = RecoveryPlanningService(
        DEFAULT_CONTEXT_SERVICE, FakePlanner(error=PlannerUnavailableError("OpenAI request timed out"))
    )
    with pytest.raises(PlannerUnavailableError, match="timed out"):
        service.analyze(ACME)


def test_invalid_dependency_change_is_rejected_by_scheduler() -> None:
    evidence = RecoveryPlanningService(DEFAULT_CONTEXT_SERVICE, FakePlanner()).evidence_for(ACME)
    payload = valid_payload(evidence[0].incident.id)
    payload["proposed_task_changes"] = [
        {
            "action": "change_dependency",
            "task_id": "acme-discovery",
            "predecessor_ids": ["acme-go-live"],
            "rationale": "Creates a cycle and must fail.",
        }
    ]
    service = RecoveryPlanningService(DEFAULT_CONTEXT_SERVICE, FakePlanner(payload))
    with pytest.raises(Exception, match="Dependency cycle"):
        service.analyze(ACME)
