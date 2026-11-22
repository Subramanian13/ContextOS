import { expect, test } from '@playwright/test'
import { project, schedule } from '../src/test/fixtures'
import { recoveryProfile } from '../src/test/recoveryFixture'

const scenario = {
  name:'Credentials available 2026-11-23',actual:schedule,
  baseline:{...schedule,forecast_completion:'2026-12-04',forecast_status:'conditional',unscheduled_task_ids:[]},
  proposed:{...schedule,forecast_completion:'2026-12-02',forecast_status:'conditional',unscheduled_task_ids:[]},
  working_days_saved:2,tasks_moved:['build'],critical_path_added:[],critical_path_removed:['build'],
  baseline_resource_utilization:[],proposed_resource_utilization:[],remaining_blockers:[],feasibility:'conditional',
  explanation:'The deterministic schedule finishes 2 working days earlier under the same assumptions.',
  causal_explanation:'Reassigning connector validation frees QA to start integration testing earlier.',
  assumptions:['Customer date is hypothetical.'],projection_only:true,
}

test('successful review, approval, execution, and audit workflow', async ({page}) => {
  let status='draft'; let proposals:any[]=[]; let audits:any[]=[]; let currentProject=project
  await page.route('**/api/v1/**', async route => {
    const url=new URL(route.request().url()); const path=url.pathname; const method=route.request().method()
    const reply=(json:unknown,statusCode=200)=>route.fulfill({status:statusCode,contentType:'application/json',body:JSON.stringify(json)})
    if(path.endsWith('/environment')) return reply({environment:'demo',synthetic_data:true,write_enabled:true,authentication:'demo_operator_only'})
    if(path.endsWith('/schedule')) return reply(schedule)
    if(path.endsWith('/recovery/profile')) return reply(recoveryProfile)
    if(path.endsWith('/recovery/scenarios')) return reply(scenario)
    if(path.endsWith('/audit-events')) return reply(audits)
    if(path.endsWith('/recovery/proposals')&&method==='GET') return reply(proposals)
    if(path.endsWith('/recovery/proposals')&&method==='POST') { proposals=[proposal('draft')]; return reply(proposals[0]) }
    if(path.endsWith('/submit')) status='pending_approval'
    if(path.endsWith('/approve')) status='approved'
    if(path.endsWith('/execute')) { status='executed'; currentProject={...project,version:2}; audits=[audit('proposal_executed')]; proposals=[proposal(status,true)]; return reply(proposals[0]) }
    if(path.endsWith('/submit')||path.endsWith('/approve')) { proposals=[proposal(status)]; audits=[audit(`proposal_${status==='pending_approval'?'submitted':'approved'}`)]; return reply(proposals[0]) }
    return reply(currentProject)
  })
  page.on('dialog',dialog=>dialog.accept())
  await page.goto('/projects/acme-crm/recovery')
  await expect(page.getByText('What-if recovery scenario')).toBeVisible()
  await page.getByRole('button',{name:'Compare recovery plans'}).click()
  await expect(page.getByText('Why this plan helps')).toBeVisible()
  await page.getByRole('button',{name:'Save recovery proposal'}).click()
  await expect(page.getByText('2 working days').last()).toBeVisible()
  await page.getByText('Review exact changes, assumptions, and evidence').click()
  await expect(page.getByText('No historical evidence attached. This proposal was created from a scheduling simulation.')).toBeVisible()
  await page.getByRole('button',{name:'Submit for approval'}).click()
  await page.getByRole('button',{name:'Approve proposal'}).click()
  await page.getByRole('button',{name:'Execute approved changes'}).click()
  await expect(page.getByText(/Approved changes were applied and verified at project version 2/)).toBeVisible()
  await expect(page.getByText(/Actual forecast: unresolved/)).toBeVisible()
  await expect(page.getByText(/proposal executed/)).toBeVisible()
})

test('provider failure remains explicit and does not fabricate a proposal', async ({page}) => {
  await page.route('**/api/v1/**', route => {
    const path=new URL(route.request().url()).pathname
    const value=path.endsWith('/schedule')?schedule:path.endsWith('/recovery/proposals')||path.endsWith('/audit-events')?[]:path.endsWith('/environment')?{environment:'demo',synthetic_data:true,write_enabled:false,authentication:'read_only'}:project
    if(path.endsWith('/recovery/analyze')) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'OpenAI request timed out'})})
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)})
  })
  await page.goto('/projects/acme-crm/recovery')
  await page.getByRole('button',{name:'Analyze recovery options'}).click()
  await expect(page.getByText('Recovery analysis is unavailable')).toBeVisible()
  await expect(page.getByText(/No proposal has been substituted/)).toBeVisible()
  await expect(page.getByText(/OpenAI/i)).toHaveCount(0)
})

function proposal(state:string,executed=false){return {id:'rp-e2e-0001',project_id:'acme-crm',project_version:1,title:'Salesforce recovery — 2026-11-23',proposed_changes:[{task_id:'build',resource_id:'eng'}],evidence_references:[],scenario_assumptions:['Customer date is hypothetical.'],unblock_dates:{'credentials':'2026-11-23'},customer_followups:[],simulation_results:{working_days_saved:2,proposed:{forecast_completion:'2026-12-02',deadline:'2026-11-30'}},status:state,created_at:new Date().toISOString(),updated_at:new Date().toISOString(),submitted_at:null,decided_at:null,executed_at:executed?new Date().toISOString():null,approver_identity:state==='approved'||executed?'Demo operator':null,rejection_reason:null,execution_result:executed?{project_version:2,applied_changes:[],customer_followups:[],remaining_blockers:['credentials'],actual_schedule:schedule,conditional_schedule:{...schedule,forecast_completion:'2026-12-02',forecast_status:'conditional'}}:null}}
function audit(action:string){return {id:'ae-1',project_id:'acme-crm',proposal_id:'rp-e2e-0001',actor:'Demo operator',action,before_state:{},after_state:{},occurred_at:new Date().toISOString(),execution_result:null}}
