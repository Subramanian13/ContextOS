from __future__ import annotations

from dataclasses import replace
import os

from app.domain.models import Project, Schedule
from app.domain.scheduler import ScheduleValidationError, calculate_schedule, compare_schedules
from app.schemas import (
    RecoveryScenarioRequest,
    ResourceUtilizationResponse,
    SimulationRequest,
)
from app.seed import PROJECT_BY_ID, PROJECTS


class ProjectNotFoundError(LookupError):
    pass


def get_project(project_id: str) -> Project:
    try:
        project = PROJECT_BY_ID[project_id]
    except KeyError as exc:
        raise ProjectNotFoundError(project_id) from exc
    if os.getenv("PROJECT_STORE", "postgres").lower() == "postgres":
        from app.workflow import configured_workflow_service
        return configured_workflow_service().project_state(project)
    return project


def list_projects() -> tuple[Project, ...]:
    return tuple(get_project(project.id) for project in PROJECTS)


def simulate(project: Project, request: SimulationRequest) -> tuple[Schedule, Schedule, int | None]:
    candidate = build_candidate(project, request)
    baseline = calculate_schedule(project)
    projected = calculate_schedule(candidate, unblock_dates=request.unblock_dates)
    return baseline, projected, compare_schedules(baseline, projected)


def build_candidate(project: Project, request: SimulationRequest) -> Project:
    changes_by_id = {change.task_id: change for change in request.task_changes}
    if len(changes_by_id) != len(request.task_changes):
        raise ScheduleValidationError("Each task may be changed only once")
    known_task_ids = {task.id for task in project.tasks}
    unknown = sorted(set(changes_by_id) - known_task_ids)
    if unknown:
        raise ScheduleValidationError(f"Unknown task(s): {', '.join(unknown)}")
    known_blockers = {blocker.id for blocker in project.blockers}
    unknown_blockers = sorted(set(request.unblock_dates) - known_blockers)
    if unknown_blockers:
        raise ScheduleValidationError(f"Unknown blocker(s): {', '.join(unknown_blockers)}")

    changed_tasks = []
    for task in project.tasks:
        change = changes_by_id.get(task.id)
        if not change:
            changed_tasks.append(task)
            continue
        if change.duration_days is not None and change.duration_days < task.duration_days:
            raise ScheduleValidationError(
                f"Task {task.id} duration cannot be shortened from {task.duration_days} days"
            )
        if change.predecessor_ids is not None and not set(task.predecessor_ids).issubset(
            change.predecessor_ids
        ):
            raise ScheduleValidationError(
                f"Task {task.id} cannot remove required dependencies"
            )
        changed_tasks.append(
            task.with_changes(
                duration_days=change.duration_days,
                predecessor_ids=(
                    tuple(change.predecessor_ids) if change.predecessor_ids is not None else None
                ),
                resource_id=change.resource_id,
            )
        )
    candidate = replace(project, tasks=tuple(changed_tasks))
    # Validate graph, resource existence, and qualifications before returning it.
    calculate_schedule(candidate, unblock_dates=request.unblock_dates)
    return candidate


def compare_recovery_scenario(project: Project, request: RecoveryScenarioRequest):
    simulation = SimulationRequest(
        unblock_dates=request.unblock_dates,
        task_changes=request.task_changes,
    )
    candidate = build_candidate(project, simulation)
    actual = calculate_schedule(project)
    # Fair comparison: both schedules receive identical external assumptions.
    baseline = calculate_schedule(project, unblock_dates=request.unblock_dates)
    proposed = calculate_schedule(candidate, unblock_dates=request.unblock_dates)
    saved = compare_schedules(baseline, proposed)
    before = {item.task_id: item for item in baseline.tasks}
    after = {item.task_id: item for item in proposed.tasks}
    changed_resources = {
        change.task_id for change in request.task_changes if change.resource_id is not None
    }
    moved = sorted(
        task_id for task_id in before
        if before[task_id].start_date != after[task_id].start_date
        or before[task_id].completion_date != after[task_id].completion_date
        or task_id in changed_resources
    )
    remaining = sorted(
        blocker.id for blocker in project.blockers
        if not blocker.condition_satisfied and blocker.id not in request.unblock_dates
    )
    if proposed.forecast_completion is None:
        explanation = "No completion forecast is available because required blockers remain unresolved."
    elif saved is not None and saved > 0:
        explanation = f"The deterministic schedule finishes {saved} working days earlier under the same assumptions."
    elif saved == 0:
        explanation = "The proposal is feasible but does not improve the completion forecast."
    else:
        explanation = "The proposal does not improve the completion forecast."
    causal_explanation = _causal_explanation(project, candidate, baseline, proposed, request, saved)
    return {
        "actual": actual,
        "baseline": baseline,
        "proposed": proposed,
        "working_days_saved": saved,
        "tasks_moved": moved,
        "critical_path_added": sorted(set(proposed.critical_path) - set(baseline.critical_path)),
        "critical_path_removed": sorted(set(baseline.critical_path) - set(proposed.critical_path)),
        "baseline_resource_utilization": resource_utilization(project, baseline),
        "proposed_resource_utilization": resource_utilization(candidate, proposed),
        "remaining_blockers": remaining,
        "feasibility": proposed.forecast_status,
        "explanation": explanation,
        "causal_explanation": causal_explanation,
    }


def _causal_explanation(project: Project, candidate: Project, baseline: Schedule, proposed: Schedule, request: RecoveryScenarioRequest, saved: int | None) -> str:
    if not saved or saved <= 0:
        return "The validated scheduling trace does not show an earlier project completion."
    tasks = {task.id: task for task in project.tasks}
    resources = {resource.id: resource for resource in project.resources}
    before = {item.task_id: item for item in baseline.tasks}
    after = {item.task_id: item for item in proposed.tasks}
    successors: dict[str, set[str]] = {task.id:set() for task in project.tasks}
    for task in project.tasks:
        for predecessor in task.predecessor_ids:
            successors[predecessor].add(task.id)
    def descends(task_id: str, predecessor_id: str) -> bool:
        stack=list(successors.get(predecessor_id,set())); seen=set()
        while stack:
            current=stack.pop()
            if current==task_id:return True
            if current not in seen:seen.add(current);stack.extend(successors.get(current,set()))
        return False
    finish = next((task for task in project.tasks if after[task.id].completion_date == proposed.forecast_completion), None)
    for change in request.task_changes:
        task=tasks.get(change.task_id)
        if not task or not task.resource_id or not change.resource_id or task.resource_id==change.resource_id:
            continue
        moved = next((other for other in project.tasks if other.resource_id==task.resource_id and other.id!=task.id and before[other.id].start_date and after[other.id].start_date and after[other.id].start_date < before[other.id].start_date and (not finish or descends(finish.id,other.id))),None)
        if moved:
            original=resources[task.resource_id].name; replacement=resources[change.resource_id].name
            finish_text=f" {finish.name} consequently finishes {saved} working days sooner." if finish else f" Project completion moves {saved} working days earlier."
            return f"Reassigning {task.name} from {original} to {replacement} frees {original} to start {moved.name} earlier.{finish_text}"
    return f"The validated task and resource schedule moves final completion {saved} working days earlier."


def resource_utilization(project: Project, schedule: Schedule) -> list[ResourceUtilizationResponse]:
    scheduled = {item.task_id for item in schedule.tasks if item.start_date is not None}
    return [
        ResourceUtilizationResponse(
            resource_id=resource.id,
            scheduled_working_days=sum(
                task.duration_days for task in project.tasks
                if task.id in scheduled and task.resource_id == resource.id
            ),
            task_count=sum(
                1 for task in project.tasks
                if task.id in scheduled and task.resource_id == resource.id
            ),
        )
        for resource in project.resources
    ]

