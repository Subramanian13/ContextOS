from dataclasses import replace
from datetime import date

import pytest

from app.domain.models import Blocker, CredentialReadiness, Project, Resource, Task
from app.domain.scheduler import DependencyCycleError, ScheduleValidationError, calculate_schedule
from app.schemas import RecoveryScenarioRequest, SimulationRequest, TaskChangeRequest
from app.seed import ACME
from app.service import compare_recovery_scenario, simulate


def project_with(*tasks: Task, blockers: tuple[Blocker, ...] = ()) -> Project:
    return Project("p", "P", "C", "Type", date(2026, 11, 16), date(2026, 11, 30), 1, tasks, (Resource("r", "R", date(2026, 11, 16)),), blockers)


def test_dependency_cycle_is_rejected() -> None:
    project = project_with(Task("a", "A", 1, ("b",)), Task("b", "B", 1, ("a",)))
    with pytest.raises(DependencyCycleError):
        calculate_schedule(project)


def test_blocker_and_dependants_remain_unscheduled_without_assumption() -> None:
    project = project_with(Task("a", "A", 1, blocker_id="credential"), Task("b", "B", 1, ("a",)), blockers=(Blocker("credential", "Missing credential"),))
    schedule = calculate_schedule(project)
    assert schedule.unscheduled_task_ids == ("a", "b")
    assert schedule.forecast_completion is None
    assert schedule.forecast_status == "unresolved"


def test_explicit_unblock_assumption_enables_schedule() -> None:
    schedule = calculate_schedule(ACME, unblock_dates={"acme-api-credentials": date(2026, 11, 20)})
    assert schedule.forecast_completion == date(2026, 12, 3)
    assert schedule.unscheduled_task_ids == ()
    assert schedule.critical_path[-1] == "acme-go-live"
    assert schedule.forecast_status == "conditional"
    assert schedule.forecast_assumptions == (
        "Simulation assumes the API credentials blocker is resolved on November 20, 2026. Actual blocker remains open.",
    )


def test_resource_availability_serializes_independent_tasks() -> None:
    project = project_with(Task("a", "A", 2, resource_id="r"), Task("b", "B", 2, resource_id="r"))
    schedule = calculate_schedule(project)
    by_id = {task.task_id: task for task in schedule.tasks}
    assert by_id["a"].completion_date == date(2026, 11, 17)
    assert by_id["b"].start_date == date(2026, 11, 18)
    assert schedule.critical_path == ("a", "b")


def test_missing_predecessor_is_rejected() -> None:
    with pytest.raises(ScheduleValidationError, match="missing predecessor"):
        calculate_schedule(project_with(Task("a", "A", 1, ("missing",))))


def test_simulation_rejects_silent_duration_reduction() -> None:
    request = SimulationRequest(task_changes=[TaskChangeRequest(task_id="acme-api-build", duration_days=2)])
    with pytest.raises(ScheduleValidationError, match="cannot be shortened"):
        simulate(ACME, request)


def test_simulation_rejects_cycle_from_dependency_change() -> None:
    request = SimulationRequest(task_changes=[TaskChangeRequest(task_id="acme-discovery", predecessor_ids=["acme-go-live"])])
    with pytest.raises(DependencyCycleError):
        simulate(ACME, request)


def test_simulation_never_mutates_project_tasks() -> None:
    original = ACME.tasks
    request = SimulationRequest(
        task_changes=[
            TaskChangeRequest(task_id="acme-security-review", resource_id="qa")
        ]
    )
    simulate(ACME, request)
    assert ACME.tasks == original
    assert next(task for task in ACME.tasks if task.id == "acme-security-review").resource_id == "eng"


@pytest.mark.parametrize(
    "readiness,scheduled",
    [
        (CredentialReadiness.NOT_REQUESTED, False),
        (CredentialReadiness.REQUESTED, False),
        (CredentialReadiness.AWAITING_CUSTOMER, False),
        (CredentialReadiness.RECEIVED, False),
        (CredentialReadiness.VALIDATED, True),
    ],
)
def test_only_validated_credentials_satisfy_authentication(readiness, scheduled) -> None:
    blocker = Blocker(
        "auth", "OAuth credentials required", condition_satisfied=True,
        credential_readiness=readiness,
    )
    result = calculate_schedule(project_with(Task("a", "Authenticate", 1, blocker_id="auth"), blockers=(blocker,)))
    assert (result.forecast_completion is not None) is scheduled


def test_unqualified_resource_reassignment_is_rejected() -> None:
    request = SimulationRequest(
        unblock_dates={"acme-api-credentials": date(2026, 11, 23)},
        task_changes=[TaskChangeRequest(task_id="acme-api-build", resource_id="impl")],
    )
    with pytest.raises(ScheduleValidationError, match="not qualified"):
        simulate(ACME, request)


def test_required_dependency_cannot_be_removed() -> None:
    request = SimulationRequest(
        task_changes=[TaskChangeRequest(task_id="acme-go-live", predecessor_ids=[])]
    )
    with pytest.raises(ScheduleValidationError, match="cannot remove required dependencies"):
        simulate(ACME, request)


def test_recovery_scenario_calculates_two_day_parallelization_gain() -> None:
    request = RecoveryScenarioRequest(
        name="November 23 credential scenario",
        unblock_dates={"acme-api-credentials": date(2026, 11, 23)},
        task_changes=[
            TaskChangeRequest(task_id="acme-sandbox-validation", resource_id="eng")
        ],
        assumptions=["Credential validation on November 23 is hypothetical."],
    )
    result = compare_recovery_scenario(ACME, request)
    assert result["actual"].forecast_status == "unresolved"
    assert result["baseline"].forecast_completion == date(2026, 12, 4)
    assert result["proposed"].forecast_completion == date(2026, 12, 2)
    assert result["working_days_saved"] == 2
    assert "acme-sandbox-validation" in result["tasks_moved"]
    assert ACME.blockers[0].condition_satisfied is False
    tasks = {task.id: task for task in ACME.tasks}
    resources = {resource.id: resource for resource in ACME.resources}
    proposed = {task.task_id: task for task in result["proposed"].tasks}
    # Integration testing does not depend on sandbox validation; both may run after connector build.
    assert "acme-sandbox-validation" not in tasks["acme-integration-test"].predecessor_ids
    assert proposed["acme-sandbox-validation"].start_date == date(2026, 11, 27)
    assert proposed["acme-integration-test"].start_date == date(2026, 11, 27)
    # The replacement engineer is available and explicitly qualified for validation.
    assert resources["eng"].available_from <= proposed["acme-sandbox-validation"].start_date
    assert tasks["acme-sandbox-validation"].required_capability in resources["eng"].capabilities
    assert "frees QA specialist to start Execute integration tests earlier" in result["causal_explanation"]


def test_no_change_scenario_does_not_claim_improvement() -> None:
    request = RecoveryScenarioRequest(
        name="Baseline only",
        unblock_dates={"acme-api-credentials": date(2026, 11, 23)},
    )
    result = compare_recovery_scenario(ACME, request)
    assert result["working_days_saved"] == 0
    assert "does not improve" in result["explanation"]

