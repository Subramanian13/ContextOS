from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.domain.scheduler import ScheduleValidationError, calculate_schedule
from app.historical import DEFAULT_CONTEXT_SERVICE
from app.recovery import ProposedTaskChange, RecoveryProposal
from app.schemas import SimulationRequest, TaskChangeRequest
from app.seed import ACME
from app.service import build_candidate


@dataclass
class EvaluationReport:
    scenarios: int
    retrieval_recall_at_5: float
    retrieval_mrr: float
    evidence_citation_validity: float
    structured_output_validity: float
    unsupported_action_rate: float
    schedule_feasibility_rate: float
    approval_safety: float
    execution_correctness: float


def load_scenarios() -> list[dict]:
    path = Path(__file__).parents[1] / "evaluation" / "scenarios.json"
    return json.loads(path.read_text())


def evaluate() -> EvaluationReport:
    rows = load_scenarios()
    recalls: list[float] = []; reciprocal_ranks: list[float] = []
    citation_valid: list[bool] = []; structured_valid: list[bool] = []
    unsupported: list[bool] = []; schedule_feasible: list[bool] = []
    approval_correct: list[bool] = []; execution_correct: list[bool] = []
    for row in rows:
        retrieved = DEFAULT_CONTEXT_SERVICE.retrieve(row["query"], 5)
        retrieved_ids = [item.incident.id for item in retrieved]
        expected = set(row["expected_evidence"])
        recalls.append(len(expected & set(retrieved_ids)) / len(expected))
        ranks = [retrieved_ids.index(item) + 1 for item in expected if item in retrieved_ids]
        reciprocal_ranks.append(1 / min(ranks) if ranks else 0)
        plan = row["plan"]
        cited = ["INC-999"] if plan == "invalid_citation" else [retrieved_ids[0]]
        citation_ok = set(cited).issubset(retrieved_ids)
        citation_valid.append(citation_ok)
        proposal_ok = True; unsupported_action = plan == "unsupported_action"
        try:
            payload = _proposal_payload(cited, plan)
            RecoveryProposal.model_validate(payload)
        except ValidationError:
            proposal_ok = False
        structured_valid.append(proposal_ok)
        unsupported.append(unsupported_action)
        task_changes = _task_changes(plan)
        scheduler_ok = True
        try:
            candidate = build_candidate(ACME, SimulationRequest(task_changes=task_changes, unblock_dates={"acme-api-credentials": date(2026, 11, 23)} if row["unblock"] else {}))
            schedule = calculate_schedule(candidate, unblock_dates={"acme-api-credentials": date(2026, 11, 23)} if row["unblock"] else {})
        except (ScheduleValidationError, ValidationError):
            scheduler_ok = False; schedule = None
        schedule_feasible.append(scheduler_ok)
        approval_allowed = proposal_ok and citation_ok and not unsupported_action and scheduler_ok
        approval_correct.append(approval_allowed == row["expected_approval"])
        execution_correct.append(not approval_allowed or (schedule is not None and ACME.blockers[0].condition_satisfied is False))
    count = len(rows)
    return EvaluationReport(
        scenarios=count,
        retrieval_recall_at_5=sum(recalls)/count,
        retrieval_mrr=sum(reciprocal_ranks)/count,
        evidence_citation_validity=sum(citation_valid)/count,
        structured_output_validity=sum(structured_valid)/count,
        unsupported_action_rate=sum(unsupported)/count,
        schedule_feasibility_rate=sum(schedule_feasible)/count,
        approval_safety=sum(approval_correct)/count,
        execution_correctness=sum(execution_correct)/count,
    )


def _proposal_payload(cited: list[str], plan: str) -> dict:
    changes = []
    if plan == "unsupported_action":
        changes = [{"action":"delete_task","task_id":"acme-api-build","rationale":"Invalid action"}]
    elif plan == "invalid_structure":
        return {"root_cause_explanation":"Missing required fields"}
    return {"root_cause_explanation":"Synthetic evaluation explanation.","supporting_evidence_ids":cited,"recommended_actions":["Review the deterministic option."],"proposed_task_changes":changes,"required_customer_actions":[],"assumptions":[],"risks":[],"reasoning_summary":"Synthetic regression case.","expected_outcome_explanation":"Scheduler decides the outcome."}


def _task_changes(plan: str) -> list[TaskChangeRequest]:
    if plan == "valid_reassign": return [TaskChangeRequest(task_id="acme-sandbox-validation", resource_id="eng")]
    if plan == "invalid_resource": return [TaskChangeRequest(task_id="acme-api-build", resource_id="impl")]
    if plan == "invalid_dependency": return [TaskChangeRequest(task_id="acme-discovery", predecessor_ids=["acme-go-live"])]
    if plan == "remove_dependency": return [TaskChangeRequest(task_id="acme-go-live", predecessor_ids=[])]
    return []


def live_subset(limit: int) -> dict:
    from app import config as _config
    from app.context_config import configured_context_service
    from app.recovery import configured_recovery_service
    rows = load_scenarios()[:limit]
    service = configured_context_service()
    results = []
    for row in rows:
        matches = service.retrieve(row["query"], 5)
        ids = [item.incident.id for item in matches]
        results.append({"id": row["id"], "retrieved": ids, "expected": row["expected_evidence"], "hit": bool(set(ids) & set(row["expected_evidence"]))})
    generation: dict
    try:
        evidence, proposal, baseline, projected = configured_recovery_service(service).analyze(ACME)
        retrieved_ids = {item.incident.id for item in evidence}
        generation = {
            "project_id": ACME.id,
            "structured_output_valid": True,
            "citation_valid": set(proposal.supporting_evidence_ids).issubset(retrieved_ids),
            "supported_actions_only": all(item.action in {"change_dependency", "reassign_resource"} for item in proposal.proposed_task_changes),
            "scheduler_validated": True,
            "actual_forecast_status": baseline.forecast_status,
            "projected_forecast_status": projected.forecast_status,
        }
    except Exception as exc:
        generation = {"project_id": ACME.id, "structured_output_valid": False, "error_class": type(exc).__name__}
    return {"provider":"OpenAI embeddings and structured Responses + PostgreSQL/pgvector","scenarios":results,"generation":generation}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--live", action="store_true"); parser.add_argument("--live-limit", type=int, default=2); parser.add_argument("--output")
    args = parser.parse_args()
    report = {"deterministic": asdict(evaluate())}
    if args.live: report["live_subset"] = live_subset(max(1, min(args.live_limit, 3)))
    rendered = json.dumps(report, indent=2)
    if args.output: Path(args.output).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__": main()
