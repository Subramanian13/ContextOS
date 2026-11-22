from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum


class ProjectStatus(StrEnum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"


class ForecastStatus(StrEnum):
    FEASIBLE = "feasible"
    CONDITIONAL = "conditional"
    UNRESOLVED = "unresolved"


class CredentialReadiness(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    AWAITING_CUSTOMER = "awaiting_customer"
    RECEIVED = "received"
    VALIDATED = "validated"


@dataclass(frozen=True, slots=True)
class Resource:
    id: str
    name: str
    available_from: date
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Blocker:
    id: str
    description: str
    condition_satisfied: bool = False
    satisfied_on: date | None = None
    owner: str = "customer"
    credential_readiness: CredentialReadiness | None = None
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    name: str
    duration_days: int
    predecessor_ids: tuple[str, ...] = ()
    resource_id: str | None = None
    blocker_id: str | None = None
    milestone: str | None = None
    required_capability: str | None = None

    def with_changes(
        self,
        *,
        duration_days: int | None = None,
        predecessor_ids: tuple[str, ...] | None = None,
        resource_id: str | None = None,
    ) -> Task:
        return replace(
            self,
            duration_days=self.duration_days if duration_days is None else duration_days,
            predecessor_ids=self.predecessor_ids if predecessor_ids is None else predecessor_ids,
            resource_id=self.resource_id if resource_id is None else resource_id,
        )


@dataclass(frozen=True, slots=True)
class ProjectEvent:
    id: str
    occurred_at: datetime
    kind: str
    summary: str


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    name: str
    customer: str
    project_type: str
    start_date: date
    deadline: date
    version: int
    tasks: tuple[Task, ...]
    resources: tuple[Resource, ...]
    blockers: tuple[Blocker, ...] = ()
    events: tuple[ProjectEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    task_id: str
    start_date: date | None
    completion_date: date | None
    critical: bool
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Schedule:
    project_id: str
    project_version: int
    calculated_at: datetime
    tasks: tuple[ScheduledTask, ...]
    forecast_completion: date | None
    deadline: date
    variance_working_days: int | None
    critical_path: tuple[str, ...]
    unscheduled_task_ids: tuple[str, ...] = field(default_factory=tuple)
    forecast_status: ForecastStatus = ForecastStatus.FEASIBLE
    forecast_assumptions: tuple[str, ...] = field(default_factory=tuple)

