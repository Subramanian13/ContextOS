import os

from fastapi import APIRouter, Depends, HTTPException

from app.domain.scheduler import ScheduleValidationError, calculate_schedule
from app.schemas import (
    BlockerResponse,
    ProjectDetailResponse,
    ProjectEventResponse,
    ProjectSummaryResponse,
    ProposalCreateRequest,
    ProposalDecisionRequest,
    ProposalExecuteRequest,
    RecoveryProposalRecordResponse,
    AuditEventResponse,
    DemoResetRequest,
    ResourceResponse,
    RecoveryScenarioRequest,
    RecoveryAnalysisRequest,
    RecoveryScenarioResponse,
    ScheduleResponse,
    SimulationRequest,
    SimulationResponse,
    TaskResponse,
)
from app.service import (
    ProjectNotFoundError,
    compare_recovery_scenario,
    get_project,
    list_projects,
    simulate,
)
from app.context_config import configured_context_service
from app.ai import AIProviderError, USAGE_TRACKER
from app.recovery import (
    HistoricalEvidenceResponse,
    PlannerOutputError,
    PlannerUnavailableError,
    RecoveryAnalysisResponse,
    configured_recovery_service,
)
from app.workflow import (
    ProposalNotFoundError,
    ProposalStatus,
    WorkflowError,
    configured_workflow_service,
)
from app.security import require_demo_write
from app.recovery_profiles import profile_for

router = APIRouter(prefix="/api/v1")


def _evidence_response(item) -> HistoricalEvidenceResponse:
    incident = item.incident
    return HistoricalEvidenceResponse(
        id=incident.id,
        project_id=incident.project_id,
        project_category=incident.project_category,
        problem_description=incident.problem_description,
        root_cause=incident.root_cause,
        resolution=incident.resolution,
        outcome=incident.outcome,
        technologies=list(incident.technologies),
        evidence_source=incident.evidence_source,
        event_date=incident.event_date.isoformat(),
        retrieval_score=item.score,
    )


def _schedule_response(schedule) -> ScheduleResponse:
    return ScheduleResponse.model_validate(schedule)


@router.get("/projects", response_model=list[ProjectSummaryResponse])
def projects() -> list[ProjectSummaryResponse]:
    result = []
    for project in list_projects():
        schedule = calculate_schedule(project)
        blocked = len(schedule.unscheduled_task_ids)
        directly_blocked = sum(
            1 for task in schedule.tasks
            if task.blocked_reason and not task.blocked_reason.startswith("Waiting on")
        )
        downstream_affected = sum(
            1 for task in schedule.tasks
            if task.blocked_reason and task.blocked_reason.startswith("Waiting on")
        )
        if blocked:
            risk = "off_track"
        elif schedule.variance_working_days and schedule.variance_working_days > 0:
            risk = "at_risk"
        else:
            risk = "on_track"
        result.append(
            ProjectSummaryResponse(
                id=project.id,
                name=project.name,
                customer=project.customer,
                project_type=project.project_type,
                deadline=project.deadline,
                forecast_completion=schedule.forecast_completion,
                blocked_tasks=blocked,
                directly_blocked_tasks=directly_blocked,
                downstream_affected_tasks=downstream_affected,
                delivery_risk=risk,
                forecast_status=schedule.forecast_status,
                variance_working_days=schedule.variance_working_days,
            )
        )
    return result


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
def project_detail(project_id: str) -> ProjectDetailResponse:
    try:
        project = get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        customer=project.customer,
        project_type=project.project_type,
        start_date=project.start_date,
        deadline=project.deadline,
        version=project.version,
        tasks=[TaskResponse.model_validate(task) for task in project.tasks],
        resources=[ResourceResponse.model_validate(resource) for resource in project.resources],
        blockers=[BlockerResponse.model_validate(blocker) for blocker in project.blockers],
        events=[ProjectEventResponse.model_validate(event) for event in project.events],
    )


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def project_tasks(project_id: str) -> list[TaskResponse]:
    try:
        project = get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return [TaskResponse.model_validate(task) for task in project.tasks]


@router.get("/projects/{project_id}/recovery/profile")
def recovery_profile(project_id: str) -> dict:
    try: get_project(project_id)
    except ProjectNotFoundError as exc: raise HTTPException(status_code=404,detail="Project not found") from exc
    profile=profile_for(project_id)
    if not profile: raise HTTPException(status_code=404,detail="No supported recovery profile exists")
    return profile


@router.get("/projects/{project_id}/schedule", response_model=ScheduleResponse)
def project_schedule(project_id: str) -> ScheduleResponse:
    try:
        return _schedule_response(calculate_schedule(get_project(project_id)))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post("/projects/{project_id}/schedule/simulate", response_model=SimulationResponse)
def simulate_schedule(project_id: str, request: SimulationRequest) -> SimulationResponse:
    try:
        baseline, projected, improvement = simulate(get_project(project_id), request)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SimulationResponse(
        baseline=_schedule_response(baseline),
        projected=_schedule_response(projected),
        improvement_working_days=improvement,
    )


@router.post(
    "/projects/{project_id}/recovery/scenarios",
    response_model=RecoveryScenarioResponse,
)
def recovery_scenario(
    project_id: str, request: RecoveryScenarioRequest
) -> RecoveryScenarioResponse:
    try:
        result = compare_recovery_scenario(get_project(project_id), request)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assumptions = list(request.assumptions)
    assumptions.extend(result["proposed"].forecast_assumptions)
    return RecoveryScenarioResponse(
        name=request.name,
        actual=_schedule_response(result["actual"]),
        baseline=_schedule_response(result["baseline"]),
        proposed=_schedule_response(result["proposed"]),
        working_days_saved=result["working_days_saved"],
        tasks_moved=result["tasks_moved"],
        critical_path_added=result["critical_path_added"],
        critical_path_removed=result["critical_path_removed"],
        baseline_resource_utilization=result["baseline_resource_utilization"],
        proposed_resource_utilization=result["proposed_resource_utilization"],
        remaining_blockers=result["remaining_blockers"],
        feasibility=result["feasibility"],
        explanation=result["explanation"],
        causal_explanation=result["causal_explanation"],
        assumptions=assumptions,
    )


@router.get(
    "/projects/{project_id}/historical-context",
    response_model=list[HistoricalEvidenceResponse],
)
def historical_context(
    project_id: str,
    limit: int | None = None,
    project_category: str | None = None,
) -> list[HistoricalEvidenceResponse]:
    try:
        project = get_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    limit = limit or int(os.getenv("RETRIEVAL_TOP_K", "5"))
    if not 1 <= limit <= 12:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 12")
    query = " ".join(
        [project.project_type]
        + [task.name for task in project.tasks]
        + [blocker.description for blocker in project.blockers]
    )
    try:
        service = configured_context_service()
        if project_category and hasattr(service, "retrieve"):
            try:
                matches = service.retrieve(query, limit, project_category)
            except TypeError:
                matches = [
                    item
                    for item in service.retrieve(query, 12)
                    if item.incident.project_category == project_category
                ][:limit]
        else:
            matches = service.retrieve(query, limit)
    except (RuntimeError, AIProviderError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [_evidence_response(item) for item in matches]


@router.post(
    "/projects/{project_id}/recovery/analyze",
    response_model=RecoveryAnalysisResponse,
)
def analyze_recovery(project_id: str, request: RecoveryAnalysisRequest | None = None) -> RecoveryAnalysisResponse:
    try:
        project = get_project(project_id)
        service = configured_recovery_service(configured_context_service())
        evidence, proposal, baseline, projected = service.analyze(project, request or RecoveryAnalysisRequest())
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except (PlannerUnavailableError, RuntimeError, AIProviderError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlannerOutputError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RecoveryAnalysisResponse(
        evidence=[_evidence_response(item) for item in evidence],
        proposal=proposal,
        baseline=_schedule_response(baseline),
        projected=_schedule_response(projected),
        feasibility_status=projected.forecast_status,
        simulation_assumptions=list(projected.forecast_assumptions),
    )


@router.post("/projects/{project_id}/recovery/proposals", response_model=RecoveryProposalRecordResponse, dependencies=[Depends(require_demo_write)])
def create_recovery_proposal(project_id: str, request: ProposalCreateRequest):
    try:
        return configured_workflow_service().create(get_project(project_id), request)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/recovery/proposals", response_model=list[RecoveryProposalRecordResponse])
def recovery_proposals(project_id: str):
    try:
        get_project(project_id)
        return configured_workflow_service().list(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get("/recovery/proposals", response_model=list[RecoveryProposalRecordResponse])
def all_recovery_proposals():
    return configured_workflow_service().list_all()


@router.post("/recovery/proposals/{proposal_id}/submit", response_model=RecoveryProposalRecordResponse, dependencies=[Depends(require_demo_write)])
def submit_recovery_proposal(proposal_id: str):
    return _workflow_call(lambda: configured_workflow_service().submit(proposal_id))


@router.post("/recovery/proposals/{proposal_id}/approve", response_model=RecoveryProposalRecordResponse, dependencies=[Depends(require_demo_write)])
def approve_recovery_proposal(proposal_id: str, request: ProposalDecisionRequest):
    service=configured_workflow_service()
    def operation():
        proposal=service.get(proposal_id)
        current=get_project(proposal.project_id)
        result=service.approve(proposal_id,request,current.version)
        if result.status == ProposalStatus.STALE:
            raise HTTPException(status_code=409,detail=f"This proposal targets project version {result.project_version}. The current project version is {current.version}.")
        return result
    return _workflow_call(operation)


@router.post("/recovery/proposals/{proposal_id}/reject", response_model=RecoveryProposalRecordResponse, dependencies=[Depends(require_demo_write)])
def reject_recovery_proposal(proposal_id: str, request: ProposalDecisionRequest):
    return _workflow_call(lambda: configured_workflow_service().reject(proposal_id, request))


@router.post("/recovery/proposals/{proposal_id}/execute", response_model=RecoveryProposalRecordResponse, dependencies=[Depends(require_demo_write)])
def execute_recovery_proposal(proposal_id: str, request: ProposalExecuteRequest):
    service = configured_workflow_service()
    try:
        proposal = service.get(proposal_id)
        result = service.execute(get_project(proposal.project_id), proposal_id, request)
        if result.status == ProposalStatus.STALE:
            raise HTTPException(status_code=409, detail="Proposal is stale because the project version changed")
        return result
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proposal not found") from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}/audit-events", response_model=list[AuditEventResponse])
def project_audit_events(project_id: str):
    try:
        get_project(project_id)
        return configured_workflow_service().audit_history(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get("/audit-events", response_model=list[AuditEventResponse])
def all_audit_events():
    return configured_workflow_service().audit_history_all()


@router.post("/demo/reset", dependencies=[Depends(require_demo_write)])
def reset_demo(request: DemoResetRequest) -> dict:
    if os.getenv("DEMO_MODE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Demo reset is available only in the synthetic demo environment.")
    if request.confirmation != "RESET SYNTHETIC DEMO":
        raise HTTPException(status_code=422, detail="Exact reset confirmation is required.")
    result = configured_workflow_service().reset_demo_project("acme-crm")
    return {"status": "reset", "project_id": "acme-crm", "synthetic_data_only": True, "actor": request.actor, **result}


def _workflow_call(operation):
    try:
        return operation()
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proposal not found") from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/internal/usage")
def internal_usage() -> dict:
    if os.getenv("CONTEXTOS_ENV", "development") != "development":
        raise HTTPException(status_code=404, detail="Not found")
    return USAGE_TRACKER.summary()

