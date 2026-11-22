from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from typing import Mapping

from app.domain.models import (
    CredentialReadiness,
    ForecastStatus,
    Project,
    Schedule,
    ScheduledTask,
    Task,
)


class ScheduleValidationError(ValueError):
    pass


class DependencyCycleError(ScheduleValidationError):
    pass


def is_working_day(value: date) -> bool:
    return value.weekday() < 5


def next_working_day(value: date) -> date:
    result = value
    while not is_working_day(result):
        result += timedelta(days=1)
    return result


def working_day_after(value: date) -> date:
    return next_working_day(value + timedelta(days=1))


def add_working_days(start: date, duration_days: int) -> date:
    if duration_days < 1:
        raise ScheduleValidationError("Task duration must be at least one working day")
    result = next_working_day(start)
    for _ in range(duration_days - 1):
        result = working_day_after(result)
    return result


def working_days_between(start: date, end: date) -> int:
    if start == end:
        return 0
    direction = 1 if end > start else -1
    current = start
    count = 0
    while current != end:
        current += timedelta(days=direction)
        if is_working_day(current):
            count += direction
    return count


def _topological_order(tasks: tuple[Task, ...]) -> list[str]:
    by_id = {task.id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ScheduleValidationError("Task IDs must be unique")
    incoming = {task.id: len(task.predecessor_ids) for task in tasks}
    successors: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        if task.duration_days < 1:
            raise ScheduleValidationError(f"Task {task.id} has an invalid duration")
        for predecessor_id in task.predecessor_ids:
            if predecessor_id not in by_id:
                raise ScheduleValidationError(
                    f"Task {task.id} references missing predecessor {predecessor_id}"
                )
            if predecessor_id == task.id:
                raise DependencyCycleError(f"Task {task.id} depends on itself")
            successors[predecessor_id].append(task.id)
    queue = deque(task.id for task in tasks if incoming[task.id] == 0)
    order: list[str] = []
    while queue:
        task_id = queue.popleft()
        order.append(task_id)
        for successor_id in successors[task_id]:
            incoming[successor_id] -= 1
            if incoming[successor_id] == 0:
                queue.append(successor_id)
    if len(order) != len(tasks):
        cyclic = sorted(task_id for task_id, count in incoming.items() if count > 0)
        raise DependencyCycleError(f"Dependency cycle detected: {', '.join(cyclic)}")
    return order


def calculate_schedule(
    project: Project,
    *,
    unblock_dates: Mapping[str, date] | None = None,
    calculated_at: datetime | None = None,
) -> Schedule:
    unblock_dates = unblock_dates or {}
    order = _topological_order(project.tasks)
    by_id = {task.id: task for task in project.tasks}
    blockers = {blocker.id: blocker for blocker in project.blockers}
    resources = {resource.id: resource for resource in project.resources}
    completion: dict[str, date] = {}
    starts: dict[str, date] = {}
    resource_next: dict[str, date] = {
        resource.id: next_working_day(resource.available_from) for resource in project.resources
    }
    blocked_reasons: dict[str, str] = {}
    resource_predecessor: dict[str, str] = {}
    task_resource_predecessor: dict[str, str] = {}

    for task_id in order:
        task = by_id[task_id]
        missing_predecessors = [p for p in task.predecessor_ids if p not in completion]
        if missing_predecessors:
            blocked_reasons[task_id] = "Waiting on unscheduled predecessor(s): " + ", ".join(
                missing_predecessors
            )
            continue
        earliest = next_working_day(project.start_date)
        if task.predecessor_ids:
            earliest = max(working_day_after(completion[p]) for p in task.predecessor_ids)
        if task.resource_id:
            if task.resource_id not in resources:
                raise ScheduleValidationError(
                    f"Task {task.id} references missing resource {task.resource_id}"
                )
            resource = resources[task.resource_id]
            if task.required_capability and task.required_capability not in resource.capabilities:
                raise ScheduleValidationError(
                    f"Resource {resource.id} is not qualified for task {task.id} "
                    f"(requires {task.required_capability})"
                )
            earliest = max(earliest, resource_next[task.resource_id])
        if task.blocker_id:
            blocker = blockers.get(task.blocker_id)
            if blocker is None:
                raise ScheduleValidationError(
                    f"Task {task.id} references missing blocker {task.blocker_id}"
                )
            credential_is_valid = (
                blocker.credential_readiness is None
                or blocker.credential_readiness == CredentialReadiness.VALIDATED
            )
            if blocker.condition_satisfied and credential_is_valid:
                if blocker.satisfied_on:
                    earliest = max(earliest, next_working_day(blocker.satisfied_on))
            elif task.blocker_id in unblock_dates:
                earliest = max(earliest, next_working_day(unblock_dates[task.blocker_id]))
            else:
                blocked_reasons[task_id] = blocker.description
                continue
        finish = add_working_days(earliest, task.duration_days)
        starts[task_id] = earliest
        completion[task_id] = finish
        if task.resource_id:
            if task.resource_id in resource_predecessor:
                task_resource_predecessor[task_id] = resource_predecessor[task.resource_id]
            resource_predecessor[task.resource_id] = task_id
            resource_next[task.resource_id] = working_day_after(finish)

    latest_scheduled_completion = max(completion.values()) if completion else None
    critical_ids: set[str] = set()
    critical_path: list[str] = []
    if latest_scheduled_completion:
        cursor_candidates = [
            task_id for task_id, finish in completion.items() if finish == latest_scheduled_completion
        ]
        cursor = cursor_candidates[-1]
        while True:
            critical_ids.add(cursor)
            critical_path.append(cursor)
            predecessors = [p for p in by_id[cursor].predecessor_ids if p in completion]
            if cursor in task_resource_predecessor:
                predecessors.append(task_resource_predecessor[cursor])
            if not predecessors:
                break
            predecessor = max(predecessors, key=lambda p: completion[p])
            if working_day_after(completion[predecessor]) != starts[cursor]:
                break
            cursor = predecessor
        critical_path.reverse()

    scheduled_tasks = tuple(
        ScheduledTask(
            task_id=task.id,
            start_date=starts.get(task.id),
            completion_date=completion.get(task.id),
            critical=task.id in critical_ids,
            blocked_reason=blocked_reasons.get(task.id),
        )
        for task in project.tasks
    )
    unscheduled = tuple(task.id for task in project.tasks if task.id not in completion)
    assumptions = tuple(
        f"Simulation assumes the {_blocker_label(blocker_id)} blocker is resolved on "
        f"{unblock_date.strftime('%B')} {unblock_date.day}, {unblock_date.year}. "
        "Actual blocker remains open."
        for blocker_id, unblock_date in sorted(unblock_dates.items())
    )
    if unscheduled:
        forecast_status = ForecastStatus.UNRESOLVED
        forecast = None
    elif assumptions:
        forecast_status = ForecastStatus.CONDITIONAL
        forecast = latest_scheduled_completion
    else:
        forecast_status = ForecastStatus.FEASIBLE
        forecast = latest_scheduled_completion
    return Schedule(
        project_id=project.id,
        project_version=project.version,
        calculated_at=calculated_at or datetime.now(timezone.utc),
        tasks=scheduled_tasks,
        forecast_completion=forecast,
        deadline=project.deadline,
        variance_working_days=(
            working_days_between(project.deadline, forecast) if forecast else None
        ),
        critical_path=tuple(critical_path),
        unscheduled_task_ids=unscheduled,
        forecast_status=forecast_status,
        forecast_assumptions=assumptions,
    )


def compare_schedules(before: Schedule, after: Schedule) -> int | None:
    if before.forecast_completion is None or after.forecast_completion is None:
        return None
    return working_days_between(after.forecast_completion, before.forecast_completion)


def _blocker_label(blocker_id: str) -> str:
    parts = blocker_id.split("-")
    if len(parts) > 2:
        parts = parts[1:]
    return " ".join("API" if part.lower() == "api" else part for part in parts)

