import type { AuditEvent, HistoricalEvidence, PersistedRecoveryProposal, ProjectDetail, ProjectSummary, RecoveryAnalysis, RecoveryProfile, RecoveryScenario, Schedule, TaskChange } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) { super(message) }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError('The ContextOS API is unavailable. Check that the backend is running.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    throw new ApiError(body?.detail ?? (response.status === 404 ? 'Project not found.' : 'Unable to load project data.'), response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  environment: () => request<{environment:string;synthetic_data:true;write_enabled:boolean;authentication:string}>('/api/v1/environment'),
  projects: () => request<ProjectSummary[]>('/api/v1/projects'),
  project: (id: string) => request<ProjectDetail>(`/api/v1/projects/${id}`),
  schedule: (id: string) => request<Schedule>(`/api/v1/projects/${id}/schedule`),
  historicalContext: (id: string) => request<HistoricalEvidence[]>(`/api/v1/projects/${id}/historical-context`),
  analyzeRecovery: (id: string, body: {unblock_dates:Record<string,string>;assumptions:string[]}) => request<RecoveryAnalysis>(`/api/v1/projects/${id}/recovery/analyze`, { method: 'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body) }),
  recoveryProfile: (id:string) => request<RecoveryProfile>(`/api/v1/projects/${id}/recovery/profile`),
  createRecoveryScenario: (id: string, body: {name:string; unblock_dates:Record<string,string>; task_changes:TaskChange[]; assumptions:string[]}) => request<RecoveryScenario>(`/api/v1/projects/${id}/recovery/scenarios`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }),
  proposals: (id:string) => request<PersistedRecoveryProposal[]>(`/api/v1/projects/${id}/recovery/proposals`),
  allProposals: () => request<PersistedRecoveryProposal[]>('/api/v1/recovery/proposals'),
  createProposal: (id:string, body:unknown) => request<PersistedRecoveryProposal>(`/api/v1/projects/${id}/recovery/proposals`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),
  submitProposal: (id:string) => request<PersistedRecoveryProposal>(`/api/v1/recovery/proposals/${id}/submit`, {method:'POST'}),
  approveProposal: (id:string) => request<PersistedRecoveryProposal>(`/api/v1/recovery/proposals/${id}/approve`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor:'Demo operator'})}),
  rejectProposal: (id:string) => request<PersistedRecoveryProposal>(`/api/v1/recovery/proposals/${id}/reject`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor:'Demo operator',reason:'Rejected during explicit human review'})}),
  executeProposal: (id:string, key:string) => request<PersistedRecoveryProposal>(`/api/v1/recovery/proposals/${id}/execute`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actor:'Demo operator',idempotency_key:key})}),
  auditEvents: (id:string) => request<AuditEvent[]>(`/api/v1/projects/${id}/audit-events`),
  allAuditEvents: () => request<AuditEvent[]>('/api/v1/audit-events'),
  resetDemo: () => request<{status:string}>('/api/v1/demo/reset', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation:'RESET SYNTHETIC DEMO',actor:'Demo operator'})}),
}
