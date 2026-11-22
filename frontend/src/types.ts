export type RiskStatus = 'on_track' | 'at_risk' | 'off_track'

export interface ProjectSummary {
  id: string
  name: string
  customer: string
  project_type: string
  deadline: string
  forecast_completion: string | null
  blocked_tasks: number
  directly_blocked_tasks: number
  downstream_affected_tasks: number
  delivery_risk: RiskStatus
  forecast_status: ForecastStatus
  variance_working_days: number | null
}

export type ForecastStatus = 'feasible' | 'conditional' | 'unresolved'

export interface Task {
  id: string
  name: string
  duration_days: number
  predecessor_ids: string[]
  resource_id: string | null
  blocker_id: string | null
  milestone: string | null
  required_capability: string | null
}

export interface Resource { id: string; name: string; available_from: string; capabilities: string[] }
export type CredentialReadiness = 'not_requested'|'requested'|'awaiting_customer'|'received'|'validated'
export interface Blocker { id: string; description: string; condition_satisfied: boolean; satisfied_on: string | null; owner: string; credential_readiness: CredentialReadiness|null; metadata: [string,string][] }
export interface ProjectEvent { id: string; occurred_at: string; kind: string; summary: string }

export interface ProjectDetail {
  id: string
  name: string
  customer: string
  project_type: string
  start_date: string
  deadline: string
  version: number
  tasks: Task[]
  resources: Resource[]
  blockers: Blocker[]
  events: ProjectEvent[]
}

export interface ScheduledTask {
  task_id: string
  start_date: string | null
  completion_date: string | null
  critical: boolean
  blocked_reason: string | null
}

export interface Schedule {
  project_id: string
  project_version: number
  calculated_at: string
  tasks: ScheduledTask[]
  forecast_completion: string | null
  deadline: string
  variance_working_days: number | null
  critical_path: string[]
  unscheduled_task_ids: string[]
  forecast_status: ForecastStatus
  forecast_assumptions: string[]
}

export interface HistoricalEvidence {
  id: string
  project_id: string
  project_category: string
  problem_description: string
  root_cause: string
  resolution: string
  outcome: string
  technologies: string[]
  evidence_source: string
  event_date: string
  retrieval_score: number
}

export interface ProposedTaskChange {
  action: 'change_dependency' | 'reassign_resource'
  task_id: string
  predecessor_ids: string[] | null
  resource_id: string | null
  rationale: string
}

export interface RecoveryProposal {
  root_cause_explanation: string
  supporting_evidence_ids: string[]
  recommended_actions: string[]
  proposed_task_changes: ProposedTaskChange[]
  required_customer_actions: string[]
  assumptions: string[]
  risks: string[]
  reasoning_summary: string
  expected_outcome_explanation: string
}

export interface RecoveryAnalysis {
  evidence: HistoricalEvidence[]
  proposal: RecoveryProposal
  baseline: Schedule
  projected: Schedule
  feasibility_status: ForecastStatus
  simulation_assumptions: string[]
  projection_only: true
}

export interface TaskChange { task_id: string; duration_days?: number; predecessor_ids?: string[]; resource_id?: string }
export interface ResourceUtilization { resource_id: string; scheduled_working_days: number; task_count: number }
export interface RecoveryScenario {
  name: string
  actual: Schedule
  baseline: Schedule
  proposed: Schedule
  working_days_saved: number | null
  tasks_moved: string[]
  critical_path_added: string[]
  critical_path_removed: string[]
  baseline_resource_utilization: ResourceUtilization[]
  proposed_resource_utilization: ResourceUtilization[]
  remaining_blockers: string[]
  feasibility: ForecastStatus
  explanation: string
  causal_explanation: string
  assumptions: string[]
  projection_only: true
}

export interface RecoveryStrategy { id:string; title:string; description:string; task_changes:TaskChange[]; tradeoff:string }
export interface RecoveryProfile { project_id:string; title:string; summary:string; task_changes:TaskChange[]; date_blocker_id:string|null; default_assumption_date?:string; assumptions:string[]; customer_actions:string[]; strategies?:RecoveryStrategy[] }

export type ProposalStatus = 'draft'|'pending_approval'|'approved'|'rejected'|'executed'|'failed'|'stale'
export interface PersistedRecoveryProposal {
  id: string; project_id: string; project_version: number; title: string
  proposed_changes: TaskChange[]; evidence_references: string[]; scenario_assumptions: string[]
  unblock_dates: Record<string,string>; customer_followups: string[]; simulation_results: Record<string,unknown>
  status: ProposalStatus; created_at: string; updated_at: string; submitted_at: string|null
  decided_at: string|null; executed_at: string|null; approver_identity: string|null
  rejection_reason: string|null; execution_result: null|{project_version:number; applied_changes:TaskChange[]; customer_followups:string[]; remaining_blockers:string[]; actual_schedule:Schedule; conditional_schedule:Schedule}
}
export interface AuditEvent {
  id:string; project_id:string|null; proposal_id:string|null; actor:string|null; action:string|null
  before_state:Record<string,unknown>|null; after_state:Record<string,unknown>|null
  occurred_at:string; execution_result:Record<string,unknown>|null
}

