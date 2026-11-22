import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { App } from '../App'
import { project, projects, schedule } from './fixtures'
import { recoveryProfile } from './recoveryFixture'

function response(data: unknown) { return Promise.resolve({ ok:true, status:200, json:() => Promise.resolve(data) } as Response) }

afterEach(() => vi.unstubAllGlobals())

describe('ContextOS navigation and API integration', () => {
  it('derives dashboard metrics from the projects response', async () => {
    vi.stubGlobal('fetch', vi.fn(() => response(projects)))
    render(<MemoryRouter initialEntries={['/']}><App/></MemoryRouter>)
    expect(await screen.findByText('Implementation portfolio')).toBeInTheDocument()
    expect(screen.getByText('Total projects').parentElement).toHaveTextContent('2')
    expect(screen.getAllByText('On track')[0].parentElement).toHaveTextContent('1')
    expect(screen.getAllByText('Off track')[0].parentElement).toHaveTextContent('1')
    expect(screen.getByText('Unresolved blockers').parentElement).toHaveTextContent('1')
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })

  it('navigates from Acme overview to risk intelligence', async () => {
    const fetchMock=vi.fn((input: RequestInfo | URL) => String(input).endsWith('/schedule') ? response(schedule) : response(project))
    vi.stubGlobal('fetch',fetchMock)
    render(<MemoryRouter initialEntries={['/projects/acme-crm']}><App/></MemoryRouter>)
    expect(await screen.findByText('Delivery plan')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'Risk intelligence'}))
    expect(await screen.findByText('Rule-based delivery findings')).toBeInTheDocument()
    expect(screen.getByText('Customer API credentials have not been supplied.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.every(([input])=>!String(input).includes('salesforce')&&!String(input).includes('crm-context'))).toBe(true)
  })

  it('shows a working-day timeline and task details for Acme', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => String(input).endsWith('/schedule') ? response(schedule) : response(project)))
    render(<MemoryRouter initialEntries={['/projects/acme-crm/timeline']}><App/></MemoryRouter>)
    expect(await screen.findByText('Actual project timeline')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:/Solution discovery/}))
    await waitFor(() => expect(screen.getByText('Selected task')).toBeInTheDocument())
    expect(screen.getByText('2 working days')).toBeInTheDocument()
  })

  it('does not expose provider details or fabricate recovery output when analysis is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/schedule')) return response(schedule)
      if (url.endsWith('/recovery/profile')) return response(recoveryProfile)
      if (url.endsWith('/recovery/proposals') || url.endsWith('/audit-events')) return response([])
      if (url.endsWith('/historical-context')) return response([])
      if (url.endsWith('/recovery/analyze')) return Promise.resolve({ ok:false, status:503, json:() => Promise.resolve({detail:'OpenAI is not configured.'}) } as Response)
      return response(project)
    }))
    render(<MemoryRouter initialEntries={['/projects/acme-crm/recovery']}><App/></MemoryRouter>)
    await userEvent.click(await screen.findByRole('button',{name:'Analyze recovery options'}))
    expect(await screen.findByText('Recovery analysis is unavailable')).toBeInTheDocument()
    expect(screen.getByText(/No proposal has been substituted/)).toBeInTheDocument()
    expect(screen.queryByText(/OpenAI/i)).not.toBeInTheDocument()
  })

  it('creates a conditional credential scenario without changing actual status', async () => {
    const scenario = {
      name:'Credentials available 2026-11-23', actual:schedule,
      baseline:{...schedule,forecast_completion:'2026-12-04',forecast_status:'conditional',unscheduled_task_ids:[],forecast_assumptions:['Blocker credentials is resolved on 2026-11-23']},
      proposed:{...schedule,forecast_completion:'2026-12-02',forecast_status:'conditional',unscheduled_task_ids:[],forecast_assumptions:['Blocker credentials is resolved on 2026-11-23']},
      working_days_saved:2,tasks_moved:['build'],critical_path_added:[],critical_path_removed:['build'],baseline_resource_utilization:[],proposed_resource_utilization:[],remaining_blockers:[],feasibility:'conditional',explanation:'The deterministic schedule finishes 2 working days earlier under the same assumptions.',causal_explanation:'Reassigning connector validation frees QA to start integration testing earlier.',assumptions:['Simulation assumes the API credentials blocker is resolved on November 23, 2026. Actual blocker remains open.'],projection_only:true,
    }
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/schedule')) return response(schedule)
      if (url.endsWith('/recovery/profile')) return response(recoveryProfile)
      if (url.endsWith('/recovery/proposals') || url.endsWith('/audit-events')) return response([])
      if (url.endsWith('/recovery/scenarios')) return response(scenario)
      return response(project)
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter initialEntries={['/projects/acme-crm/recovery']}><App/></MemoryRouter>)
    expect(await screen.findByText('What-if recovery scenario')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Compare recovery plans'}))
    expect(await screen.findByText('2 working days saved')).toBeInTheDocument()
    expect(screen.getByText('Why this plan helps')).toBeInTheDocument()
    expect(screen.getByText(/actual project forecast remains/i)).toHaveTextContent('unresolved')
    expect(screen.getAllByText(/assumption/i).length).toBeGreaterThan(0)
    expect(screen.queryByText('Explicit assumptions')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/projects/acme-crm/recovery/scenarios', expect.objectContaining({method:'POST'}))
  })

  it('compares the exact selected project-specific recovery strategy', async () => {
    const vertex={...project,id:'vertex-financial',customer:'Vertex Financial',project_type:'Banking API integration',blockers:[],tasks:[{...project.tasks[0],id:'mapping',name:'Prepare endpoint mapping',resource_id:'backup'},{...project.tasks[1],id:'connector',name:'Build banking connector',resource_id:'critical',blocker_id:null}],resources:[{id:'critical',name:'Critical engineer',available_from:'2026-11-23',capabilities:['integration']},{id:'backup',name:'Backup engineer',available_from:'2026-11-09',capabilities:['integration']},{id:'support',name:'Support engineer',available_from:'2026-11-16',capabilities:['integration']}]}
    const vertexSchedule={...schedule,project_id:'vertex-financial',forecast_completion:'2026-12-10',forecast_status:'feasible',unscheduled_task_ids:[],tasks:[{task_id:'mapping',start_date:'2026-11-09',completion_date:'2026-11-12',critical:false,blocked_reason:null},{task_id:'connector',start_date:'2026-11-23',completion_date:'2026-11-27',critical:true,blocked_reason:null}]}
    const profile={project_id:'vertex-financial',title:'Qualified engineer reassignment',summary:'Evaluate the engineer absence.',task_changes:[{task_id:'connector',resource_id:'backup',duration_days:6}],date_blocker_id:null,assumptions:['Handoff effort is retained.'],customer_actions:[],strategies:[{id:'wait',title:'Wait for the critical engineer',description:'Keep ownership.',task_changes:[],tradeoff:'Delay remains.'},{id:'redistribute',title:'Redistribute independent API work',description:'Use qualified engineers.',task_changes:[{task_id:'mapping',resource_id:'support'},{task_id:'connector',resource_id:'backup',duration_days:6}],tradeoff:'Two handoffs.'}]}
    const scenario={name:'Redistribute independent API work',actual:vertexSchedule,baseline:vertexSchedule,proposed:{...vertexSchedule,forecast_completion:'2026-12-03'},working_days_saved:5,tasks_moved:['mapping','connector'],critical_path_added:[],critical_path_removed:[],baseline_resource_utilization:[],proposed_resource_utilization:[],remaining_blockers:[],feasibility:'feasible',explanation:'Five working days earlier.',causal_explanation:'Qualified resource changes move connector completion earlier.',assumptions:profile.assumptions,projection_only:true}
    const fetchMock=vi.fn((input:RequestInfo|URL,_init?:RequestInit)=>{const url=String(input);if(url.endsWith('/schedule'))return response(vertexSchedule);if(url.endsWith('/recovery/profile'))return response(profile);if(url.endsWith('/recovery/scenarios'))return response(scenario);if(url.endsWith('/recovery/proposals')||url.endsWith('/audit-events'))return response([]);return response(vertex)})
    vi.stubGlobal('fetch',fetchMock)
    render(<MemoryRouter initialEntries={['/projects/vertex-financial/recovery']}><App/></MemoryRouter>)
    await userEvent.click(await screen.findByRole('button',{name:/Redistribute independent API work/}))
    await userEvent.click(screen.getByRole('button',{name:'Compare recovery plans'}))
    await screen.findByText('5 working days saved')
    const scenarioCall=fetchMock.mock.calls.find(([input])=>String(input).endsWith('/recovery/scenarios'))
    const body=JSON.parse((scenarioCall?.[1] as RequestInit).body as string)
    expect(body.name).toBe('Redistribute independent API work')
    expect(body.task_changes).toHaveLength(2)
    expect(body.task_changes[1]).toEqual({task_id:'connector',resource_id:'backup',duration_days:6})
  })

})
