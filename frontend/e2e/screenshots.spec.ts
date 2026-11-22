import { expect, test } from '@playwright/test'
import { project, projects, schedule } from '../src/test/fixtures'
import { recoveryProfile } from '../src/test/recoveryFixture'

const showcaseProject = {
  ...project,
  tasks: [
    ...project.tasks,
    {
      id: 'integration',
      name: 'Execute integration tests',
      duration_days: 3,
      predecessor_ids: ['discovery'],
      resource_id: 'qa',
      blocker_id: null,
      milestone: 'Test',
      required_capability: 'validation',
    },
    {
      id: 'go-live',
      name: 'Go-live readiness',
      duration_days: 1,
      predecessor_ids: ['build', 'integration'],
      resource_id: 'impl',
      blocker_id: null,
      milestone: 'Launch',
      required_capability: 'implementation',
    },
  ],
}
const actualSchedule = {
  ...schedule,
  tasks: [
    ...schedule.tasks,
    {
      task_id: 'integration',
      start_date: '2026-11-11',
      completion_date: '2026-11-13',
      critical: false,
      blocked_reason: null,
    },
    {
      task_id: 'go-live',
      start_date: null,
      completion_date: null,
      critical: false,
      blocked_reason: 'Waiting on unscheduled predecessor(s): build',
    },
  ],
  unscheduled_task_ids: ['build', 'go-live'],
}
const baseline = {
  ...actualSchedule,
  forecast_completion: '2026-12-04',
  forecast_status: 'conditional',
  unscheduled_task_ids: [],
  tasks: [
    { ...actualSchedule.tasks[0] },
    {
      task_id: 'build',
      start_date: '2026-11-27',
      completion_date: '2026-11-30',
      critical: true,
      blocked_reason: null,
    },
    {
      task_id: 'integration',
      start_date: '2026-12-01',
      completion_date: '2026-12-03',
      critical: true,
      blocked_reason: null,
    },
    {
      task_id: 'go-live',
      start_date: '2026-12-04',
      completion_date: '2026-12-04',
      critical: true,
      blocked_reason: null,
    },
  ],
}
const proposed = {
  ...baseline,
  forecast_completion: '2026-12-02',
  tasks: [
    { ...actualSchedule.tasks[0] },
    {
      task_id: 'build',
      start_date: '2026-11-27',
      completion_date: '2026-11-30',
      critical: true,
      blocked_reason: null,
    },
    {
      task_id: 'integration',
      start_date: '2026-11-27',
      completion_date: '2026-12-01',
      critical: true,
      blocked_reason: null,
    },
    {
      task_id: 'go-live',
      start_date: '2026-12-02',
      completion_date: '2026-12-02',
      critical: true,
      blocked_reason: null,
    },
  ],
}
const comparison = {
  name: 'Acme conditional recovery',
  actual: actualSchedule,
  baseline,
  proposed,
  working_days_saved: 2,
  tasks_moved: ['build', 'integration', 'go-live'],
  critical_path_added: [],
  critical_path_removed: ['build'],
  baseline_resource_utilization: [],
  proposed_resource_utilization: [],
  remaining_blockers: [],
  feasibility: 'conditional',
  explanation: 'The deterministic schedule finishes 2 working days earlier under the same assumptions.',
  causal_explanation:
    'Reassigning Validate connector in sandbox from QA specialist to Integration engineer frees QA specialist to start Execute integration tests earlier. Go-live readiness consequently finishes 2 working days sooner.',
  assumptions: [
    'Simulation assumes the API credentials blocker is resolved on November 23, 2026. Actual blocker remains open.',
  ],
  projection_only: true,
}

const analysis = {
  evidence: [
    {
      id: 'INC-001',
      project_id: 'atlas-crm',
      project_category: 'CRM integration',
      problem_description: 'Production API credentials were missing at connector build start.',
      root_cause: 'Customer security approval was not included in the launch critical path.',
      resolution:
        'The team used a customer-approved sandbox credential for contract tests while security completed production access review.',
      outcome: 'Independent contract tests completed; production cutover remained gated until credentials were validated.',
      technologies: ['CRM', 'REST API', 'OAuth 2.0'],
      evidence_source: 'Atlas closeout / EVT-214',
      event_date: '2025-03-14',
      retrieval_score: 0.94,
    },
    {
      id: 'INC-002',
      project_id: 'borealis-crm',
      project_category: 'CRM integration',
      problem_description: 'CRM sync failed after deployment with repeated 401 responses.',
      root_cause: 'The OAuth audience differed between sandbox and production tenants.',
      resolution:
        'Integration engineering corrected the audience configuration and added a production-token validation checklist.',
      outcome: 'Authentication was restored without changing task estimates.',
      technologies: ['Salesforce', 'OAuth 2.0', 'REST API'],
      evidence_source: 'Borealis incident review / IR-88',
      event_date: '2025-06-02',
      retrieval_score: 0.885,
    },
  ],
  proposal: {
    root_cause_explanation:
      'Production OAuth 2.0 credentials for the Acme CRM integration are awaiting customer security review, blocking connector validation on the critical path.',
    supporting_evidence_ids: ['INC-001', 'INC-002'],
    recommended_actions: [
      'Reassign sandbox connector validation to an available qualified Integration Engineer once sandbox credentials are provided.',
      'Prepare contract test suites and independent QA mock validations in parallel while awaiting security clearance.',
    ],
    proposed_task_changes: [
      {
        action: 'reassign_resource',
        task_id: 'build',
        resource_id: 'eng',
        predecessor_ids: null,
        rationale: 'Reassign to qualified integration engineer to execute sandbox validation in parallel with QA preparation.',
      },
    ],
    required_customer_actions: [
      'Supply customer-approved sandbox OAuth credentials for pre-validation.',
      'Confirm security committee review date for production client secrets.',
    ],
    assumptions: [
      'Customer sandbox tenant is accessible and mirrors production schema.',
      'Integration engineer has validated capability and immediate capacity.',
    ],
    risks: [
      'Production deployment cutover remains strictly gated until live customer credentials are verified.',
    ],
    reasoning_summary:
      'Historical precedents INC-001 and INC-002 demonstrate that decoupling sandbox contract tests from live security sign-off prevents compounding downstream launch delays without taking unverified production risk.',
    expected_outcome_explanation:
      'Recovers 2 working days on connector validation, moving conditional completion from Dec 4 to Dec 2.',
  },
  baseline,
  projected: proposed,
  feasibility_status: 'conditional',
  simulation_assumptions: [
    'Simulation assumes the API credentials blocker is resolved on November 23, 2026. Actual blocker remains open.',
  ],
  projection_only: true,
}

test('capture portfolio showcase screens', async ({ page }) => {
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    let value: unknown = showcaseProject
    if (path === '/api/v1/projects') value = projects
    else if (path.endsWith('/schedule')) value = actualSchedule
    else if (path.endsWith('/recovery/profile')) value = recoveryProfile
    else if (path.endsWith('/recovery/scenarios')) value = comparison
    else if (path.endsWith('/recovery/analyze')) value = analysis
    else if (path.endsWith('/recovery/proposals') || path.endsWith('/audit-events')) value = []
    else if (path.endsWith('/environment'))
      value = { environment: 'demo', synthetic_data: true, write_enabled: false, authentication: 'read_only' }
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
  })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  await page.screenshot({ path: '../docs/screenshots/portfolio.png', fullPage: true })

  await page.goto('/projects/acme-crm/recovery')
  await page.getByRole('button', { name: 'Compare recovery plans' }).click()
  await page.screenshot({ path: '../docs/screenshots/recovery-intelligence.png', fullPage: true })

  // Capture Analyze recovery options output
  await page.goto('/projects/acme-crm/recovery')
  await page.getByRole('button', { name: 'Analyze recovery options' }).click()
  await expect(page.getByText('Grounded recovery strategies')).toBeVisible()
  await page.screenshot({ path: '../docs/screenshots/recovery-analysis.png', fullPage: true })
})
