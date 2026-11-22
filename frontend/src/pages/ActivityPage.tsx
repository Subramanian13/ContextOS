import { Activity } from 'lucide-react'
import { useEffect,useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState,LoadingState } from '../components/States'
import { api } from '../lib/api'
import type { AuditEvent,ProjectSummary } from '../types'

export function ActivityPage(){
  const [data,setData]=useState<{events:AuditEvent[];projects:ProjectSummary[]}|null>(null);const [error,setError]=useState('')
  const load=()=>{setError('');Promise.all([api.allAuditEvents(),api.projects()]).then(([events,projects])=>setData({events,projects})).catch((cause:Error)=>setError(cause.message))}
  useEffect(load,[])
  if(error)return <ErrorState message={error} retry={load}/>
  if(!data)return <LoadingState label="Loading activity history"/>
  const names=new Map(data.projects.map(item=>[item.id,item]))
  return <div className="space-y-6"><header><p className="eyebrow">Traceability</p><h1 className="mt-2 text-3xl font-semibold">Activity and audit history</h1><p className="mt-2 text-slate-600">Persisted workflow events, kept separate from analytical findings and simulations.</p></header><section className="panel overflow-hidden">{data.events.length===0?<div className="p-12 text-center"><Activity className="mx-auto text-slate-400"/><p className="mt-3 text-sm text-slate-500">No workflow activity has been recorded.</p></div>:<div className="divide-y divide-slate-100">{data.events.map(event=><article key={event.id} className="grid gap-2 p-5 sm:grid-cols-[1fr_auto]"><div><h2 className="font-semibold capitalize">{event.action?.replaceAll('_',' ')}</h2><p className="mt-1 text-sm text-slate-500">{event.project_id?names.get(event.project_id)?.customer??event.project_id:'Portfolio'} · {event.actor??'System'}</p>{event.proposal_id&&<p className="mt-1 font-mono text-xs text-slate-400">Proposal {event.proposal_id}</p>}</div><div className="text-sm text-slate-500 sm:text-right"><time>{new Date(event.occurred_at).toLocaleString()}</time>{event.project_id&&<Link className="mt-2 block font-semibold text-brand-700" to={`/projects/${event.project_id}/recovery`}>View project</Link>}</div></article>)}</div>}</section></div>
}
