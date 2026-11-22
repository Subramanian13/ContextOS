from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TaskResponse(ApiModel):
    id: str
    name: str
    duration_days: int
    predecessor_ids: tuple[str, ...]
    resource_id: str | None
    blocker_id: str | None
    milestone: str | None
    required_capability: str | None


class ResourceResponse(ApiModel):
    id: str
    name: str
    available_from: date
    capabilities: tuple[str, ...]


class BlockerResponse(ApiModel):
    id: str
    description: str
    condition_satisfied: bool
    satisfied_on: date | None
    owner: str
    credential_readiness: str | None
    metadata: tuple[tuple[str, str], ...]


class ProjectEventResponse(ApiModel):
    id: str
    occurred_at: datetime
    kind: str
    summary: str


class ProjectSummaryResponse(ApiModel):
    id: str
    name: str
    customer: str
    project_type: str
    deadline: date
    forecast_completion: date | None
    blocked_tasks: int
    directly_blocked_tasks: int
    downstream_affected_tasks: int
    delivery_risk: str
    forecast_status: str
    variance_working_days: int | None


class ProjectDetailResponse(ApiModel):
    id: str
    name: str
    customer: str
    project_type: str
    start_date: date
    deadline: date
    version: int
    tasks: list[TaskResponse]
    resources: list[ResourceResponse]
    blockers: list[BlockerResponse]
    events: list[ProjectEventResponse]


class ScheduledTaskResponse(ApiModel):
    task_id: str
    start_date: date | None
    completion_date: date | None
    critical: bool
    blocked_reason: str | None


class ScheduleResponse(ApiModel):
    project_id: str
    project_version: int
    calculated_at: datetime
    tasks: list[ScheduledTaskResponse]
    forecast_completion: date | None
    deadline: date
    variance_working_days: int | None
    critical_path: list[str]
    unscheduled_task_ids: list[str]
    forecast_status: str
    forecast_assumptions: list[str]


class TaskChangeRequest(ApiModel):
    task_id: str
    duration_days: int | None = Field(default=None, ge=1)
    predecessor_ids: list[str] | None = None
    resource_id: str | None = None


class SimulationRequest(ApiModel):
    unblock_dates: dict[str, date] = Field(default_factory=dict)
    task_changes: list[TaskChangeRequest] = Field(default_factory=list)


class SimulationResponse(ApiModel):
    baseline: ScheduleResponse
    projected: ScheduleResponse
    improvement_working_days: int | None
    projection_only: bool = True


class RecoveryScenarioRequest(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    unblock_dates: dict[str, date] = Field(default_factory=dict)
    task_changes: list[TaskChangeRequest] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class RecoveryAnalysisRequest(ApiModel):
    unblock_dates: dict[str, date] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class ResourceUtilizationResponse(ApiModel):
    resource_id: str
    scheduled_working_days: int
    task_count: int


class RecoveryScenarioResponse(ApiModel):
    name: str
    actual: ScheduleResponse
    baseline: ScheduleResponse
    proposed: ScheduleResponse
    working_days_saved: int | None
    tasks_moved: list[str]
    critical_path_added: list[str]
    critical_path_removed: list[str]
    baseline_resource_utilization: list[ResourceUtilizationResponse]
    proposed_resource_utilization: list[ResourceUtilizationResponse]
    remaining_blockers: list[str]
    feasibility: str
    explanation: str
    causal_explanation: str
    assumptions: list[str]
    projection_only: bool = True


class ProposalCreateRequest(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    unblock_dates: dict[str, date] = Field(default_factory=dict)
    task_changes: list[TaskChangeRequest] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    customer_followups: list[str] = Field(default_factory=list)


class ProposalDecisionRequest(ApiModel):
    actor: str = Field(default="Demo operator", min_length=1, max_length=160)
    reason: str | None = Field(default=None, max_length=1000)


class ProposalExecuteRequest(ApiModel):
    actor: str = Field(default="Demo operator", min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=8, max_length=160)


class RecoveryProposalRecordResponse(ApiModel):
    id: str
    project_id: str
    project_version: int
    title: str
    proposed_changes: list[dict]
    evidence_references: list[str]
    scenario_assumptions: list[str]
    unblock_dates: dict[str, str]
    customer_followups: list[str]
    simulation_results: dict
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    decided_at: datetime | None
    executed_at: datetime | None
    approver_identity: str | None
    rejection_reason: str | None
    execution_result: dict | None


class AuditEventResponse(ApiModel):
    id: str
    project_id: str | None
    proposal_id: str | None
    actor: str | None
    action: str | None
    before_state: dict | None
    after_state: dict | None
    occurred_at: datetime
    execution_result: dict | None


class DemoResetRequest(ApiModel):
    confirmation: str
    actor: str = Field(default="Demo operator", min_length=1, max_length=160)

