import { test } from '@playwright/test'
import { project, projects, schedule } from '../src/test/fixtures'
import { recoveryProfile } from '../src/test/recoveryFixture'

const showcaseProject={...project,tasks:[...project.tasks,{id:'integration',name:'Execute integration tests',duration_days:3,predecessor_ids:['discovery'],resource_id:'qa',blocker_id:null,milestone:'Test',required_capability:'validation'},{id:'go-live',name:'Go-live readiness',duration_days:1,predecessor_ids:['build','integration'],resource_id:'impl',blocker_id:null,milestone:'Launch',required_capability:'implementation'}]}
const actualSchedule={...schedule,tasks:[...schedule.tasks,{task_id:'integration',start_date:'2026-11-11',completion_date:'2026-11-13',critical:false,blocked_reason:null},{task_id:'go-live',start_date:null,completion_date:null,critical:false,blocked_reason:'Waiting on unscheduled predecessor(s): build'}],unscheduled_task_ids:['build','go-live']}
const baseline={...actualSchedule,forecast_completion:'2026-12-04',forecast_status:'conditional',unscheduled_task_ids:[],tasks:[{...actualSchedule.tasks[0]},{task_id:'build',start_date:'2026-11-27',completion_date:'2026-11-30',critical:true,blocked_reason:null},{task_id:'integration',start_date:'2026-12-01',completion_date:'2026-12-03',critical:true,blocked_reason:null},{task_id:'go-live',start_date:'2026-12-04',completion_date:'2026-12-04',critical:true,blocked_reason:null}]}
const proposed={...baseline,forecast_completion:'2026-12-02',tasks:[{...actualSchedule.tasks[0]},{task_id:'build',start_date:'2026-11-27',completion_date:'2026-11-30',critical:true,blocked_reason:null},{task_id:'integration',start_date:'2026-11-27',completion_date:'2026-12-01',critical:true,blocked_reason:null},{task_id:'go-live',start_date:'2026-12-02',completion_date:'2026-12-02',critical:true,blocked_reason:null}]}
const comparison={name:'Acme conditional recovery',actual:actualSchedule,baseline,proposed,working_days_saved:2,tasks_moved:['build','integration','go-live'],critical_path_added:[],critical_path_removed:['build'],baseline_resource_utilization:[],proposed_resource_utilization:[],remaining_blockers:[],feasibility:'conditional',explanation:'The deterministic schedule finishes 2 working days earlier under the same assumptions.',causal_explanation:'Reassigning Validate connector in sandbox from QA specialist to Integration engineer frees QA specialist to start Execute integration tests earlier. Go-live readiness consequently finishes 2 working days sooner.',assumptions:['Simulation assumes the API credentials blocker is resolved on November 23, 2026. Actual blocker remains open.'],projection_only:true}

test('capture portfolio showcase screens', async ({page}) => {
  await page.route('**/api/v1/**', route => {
    const path=new URL(route.request().url()).pathname
    let value:unknown=showcaseProject
    if(path==='/api/v1/projects') value=projects
    else if(path.endsWith('/schedule')) value=actualSchedule
    else if(path.endsWith('/recovery/profile')) value=recoveryProfile
    else if(path.endsWith('/recovery/scenarios')) value=comparison
    else if(path.endsWith('/recovery/proposals')||path.endsWith('/audit-events')) value=[]
    else if(path.endsWith('/environment')) value={environment:'demo',synthetic_data:true,write_enabled:false,authentication:'read_only'}
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)})
  })
  await page.setViewportSize({width:1440,height:1000})
  await page.goto('/')
  await page.screenshot({path:'../docs/screenshots/portfolio.png',fullPage:true})
  await page.goto('/projects/acme-crm/recovery')
  await page.getByRole('button',{name:'Compare recovery plans'}).click()
  await page.screenshot({path:'../docs/screenshots/recovery-intelligence.png',fullPage:true})
})
