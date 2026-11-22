import { FileCheck2 } from 'lucide-react'
import { useEffect,useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState,LoadingState } from '../components/States'
import { api } from '../lib/api'
import { formatDate } from '../lib/date'
import type { PersistedRecoveryProposal,ProjectSummary } from '../types'

export function ProposalsPage(){
  const [data,setData]=useState<{proposals:PersistedRecoveryProposal[];projects:ProjectSummary[]}|null>(null);const [error,setError]=useState('')
  const load=()=>{setError('');Promise.all([api.allProposals(),api.projects()]).then(([proposals,projects])=>setData({proposals,projects})).catch((cause:Error)=>setError(cause.message))}
  useEffect(load,[])
  if(error)return <ErrorState message={error} retry={load}/>
  if(!data)return <LoadingState label="Loading recovery proposals"/>
  const names=new Map(data.projects.map(item=>[item.id,item]))
  return <div className="space-y-6"><header><p className="eyebrow">Governance</p><h1 className="mt-2 text-3xl font-semibold">Recovery proposals</h1><p className="mt-2 text-slate-600">Review saved recovery plans across the portfolio. Approval and execution remain inside the relevant project workspace.</p></header><section className="panel overflow-hidden"><div className="border-b border-slate-200 px-5 py-4"><h2 className="font-semibold">Proposal register</h2><p className="mt-1 text-sm text-slate-500">{data.proposals.length} recorded proposals</p></div>{data.proposals.length===0?<div className="p-12 text-center"><FileCheck2 className="mx-auto text-slate-400"/><p className="mt-3 text-sm text-slate-500">No recovery proposals have been saved.</p></div>:<div className="divide-y divide-slate-100">{data.proposals.map(item=><article key={item.id} className="flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{item.title}</h3><span className="status-pill bg-slate-100 text-slate-700">{item.status.replaceAll('_',' ')}</span></div><p className="mt-1 text-sm text-slate-500">{names.get(item.project_id)?.customer??item.project_id} · Version {item.project_version} · {formatDate(item.created_at)}</p><p className="mt-2 text-sm text-slate-600">{item.proposed_changes.length} proposed task change{item.proposed_changes.length===1?'':'s'}</p></div><Link className="text-sm font-semibold text-brand-700" to={`/projects/${item.project_id}/recovery`}>Open proposal workflow</Link></article>)}</div>}</section></div>
}
