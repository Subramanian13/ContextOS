import { AlertOctagon, CheckCircle2, CircleAlert, Layers3, MoveRight, ShieldAlert } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState, LoadingState } from '../components/States'
import { Status } from '../components/Status'
import { api } from '../lib/api'
import { formatDate } from '../lib/date'
import type { ProjectSummary, RiskStatus } from '../types'

type SortKey = 'customer'|'status'|'deadline'

export function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status,setStatus]=useState<'all'|RiskStatus>('all')
  const [blockers,setBlockers]=useState<'all'|'blocked'|'clear'>('all')
  const [sort,setSort]=useState<SortKey>('deadline')
  const load = () => { setLoading(true); setError(''); api.projects().then(setProjects).catch((e: Error) => setError(e.message)).finally(() => setLoading(false)) }
  useEffect(load, [])
  const metrics = useMemo(() => ({total:projects.length,onTrack:projects.filter(item=>item.delivery_risk==='on_track').length,atRisk:projects.filter(item=>item.delivery_risk==='at_risk').length,offTrack:projects.filter(item=>item.delivery_risk==='off_track').length,blocked:projects.filter(item=>item.blocked_tasks>0).length}),[projects])
  const visible=useMemo(()=>projects.filter(item=>(status==='all'||item.delivery_risk===status)&&(blockers==='all'||(blockers==='blocked'?item.blocked_tasks>0:item.blocked_tasks===0))).sort((a,b)=>sort==='customer'?a.customer.localeCompare(b.customer):sort==='status'?riskRank(b.delivery_risk)-riskRank(a.delivery_risk):a.deadline.localeCompare(b.deadline)),[projects,status,blockers,sort])
  if (loading) return <LoadingState label="Loading portfolio" />
  if (error) return <ErrorState message={error} retry={load}/>
  return <div className="space-y-7">
    <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><p className="eyebrow">Portfolio</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Implementation portfolio</h1><p className="mt-2 max-w-2xl text-slate-600">See which implementations need attention and open the project workspace to investigate.</p></div><div className="flex items-center gap-2 text-sm text-slate-500"><CheckCircle2 size={17} className="text-emerald-600"/>Current backend schedule data</div></section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5" aria-label="Portfolio summary"><Metric icon={Layers3} label="Total projects" value={metrics.total}/><Metric icon={CheckCircle2} label="On track" value={metrics.onTrack} tone="green"/><Metric icon={ShieldAlert} label="At risk" value={metrics.atRisk} tone="amber"/><Metric icon={CircleAlert} label="Off track" value={metrics.offTrack} tone="red"/><Metric icon={AlertOctagon} label="Unresolved blockers" value={metrics.blocked} tone="red"/></section>
    <section className="panel overflow-hidden"><div className="flex flex-col gap-4 border-b border-slate-200 px-5 py-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between"><div><h2 className="font-semibold text-ink">Delivery portfolio</h2><p className="mt-1 text-sm text-slate-500">Actual forecasts only; simulations never replace portfolio dates.</p></div><div className="flex flex-wrap gap-2"><Filter label="Status" value={status} onChange={value=>setStatus(value as typeof status)} options={[['all','All statuses'],['on_track','On track'],['at_risk','At risk'],['off_track','Off track']]}/><Filter label="Blockers" value={blockers} onChange={value=>setBlockers(value as typeof blockers)} options={[['all','All projects'],['blocked','Has blockers'],['clear','No blockers']]}/><Filter label="Sort" value={sort} onChange={value=>setSort(value as SortKey)} options={[['deadline','Target date'],['status','Status'],['customer','Customer']]}/></div></div>
      {visible.length === 0 ? <div className="p-12 text-center text-slate-500">No projects match these filters.</div> : <div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left"><thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500"><tr><th className="px-6 py-3">Customer / project</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Planned go-live</th><th className="px-4 py-3">Forecast completion</th><th className="px-4 py-3">Schedule variance</th><th className="px-4 py-3">Active blockers</th><th className="px-6 py-3"><span className="sr-only">Open</span></th></tr></thead><tbody className="divide-y divide-slate-100">{visible.map(project => <ProjectRow key={project.id} project={project}/>)}</tbody></table></div>}
    </section>
  </div>
}

function riskRank(value:RiskStatus){return value==='off_track'?3:value==='at_risk'?2:1}
function Filter({label,value,onChange,options}:{label:string;value:string;onChange:(value:string)=>void;options:[string,string][]}){return <label className="text-xs font-medium text-slate-500">{label}<select aria-label={label} value={value} onChange={event=>onChange(event.target.value)} className="ml-2 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700">{options.map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label>}
function Metric({ icon: Icon, label, value, tone = 'blue' }: { icon: typeof Layers3; label: string; value: number; tone?: 'blue'|'green'|'red'|'amber' }) { const colors={blue:'bg-brand-50 text-brand-700',green:'bg-emerald-50 text-emerald-700',red:'bg-red-50 text-red-700',amber:'bg-amber-50 text-amber-800'}; return <div className="panel p-5"><div className="flex items-start justify-between"><div><p className="text-sm font-medium text-slate-600">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p></div><span className={`rounded-lg p-2 ${colors[tone]}`}><Icon size={19}/></span></div></div> }

function ProjectRow({ project }: { project: ProjectSummary }) {
  const variance=project.variance_working_days===null?'Cannot determine':project.variance_working_days===0?'On target':project.variance_working_days>0?`${project.variance_working_days} working days late`:`${Math.abs(project.variance_working_days)} working days early`
  return <tr className="group hover:bg-slate-50/70"><td className="px-6 py-4"><Link to={`/projects/${project.id}`} className="font-semibold text-ink group-hover:text-brand-700">{project.customer}</Link><p className="mt-1 text-sm text-slate-500">{project.project_type}</p></td><td className="px-4 py-4"><Status value={project.delivery_risk}/></td><td className="px-4 py-4 text-sm text-slate-700">{formatDate(project.deadline)}</td><td className="px-4 py-4"><p className={`text-sm font-medium ${!project.forecast_completion?'text-red-700':'text-slate-700'}`}>{project.forecast_completion?formatDate(project.forecast_completion):'Unresolved'}</p>{!project.forecast_completion&&<p className="mt-1 text-xs text-red-600">Required work is blocked</p>}</td><td className="px-4 py-4 text-sm text-slate-600">{variance}</td><td className="px-4 py-4 text-sm"><strong className={project.directly_blocked_tasks?'text-red-700':'text-slate-600'}>{project.directly_blocked_tasks} direct</strong><p className="mt-1 text-xs text-slate-500">{project.downstream_affected_tasks} downstream affected</p></td><td className="px-6 py-4 text-right"><Link aria-label={`Open ${project.customer}`} to={`/projects/${project.id}`} className="inline-flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-semibold text-brand-700 hover:bg-brand-50">Open <MoveRight size={17}/></Link></td></tr>
}
