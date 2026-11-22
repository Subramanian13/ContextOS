import { Activity, BriefcaseBusiness, FileCheck2, FolderKanban, Menu, PanelLeftClose, RotateCcw, ScrollText, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../lib/api'

export function Shell() {
  const [open, setOpen] = useState(false)
  const [environment,setEnvironment]=useState<{environment:string;write_enabled:boolean}|null>(null)
  const [resetting,setResetting]=useState(false)
  const location=useLocation()
  const currentProject=location.pathname.match(/^\/projects\/([^/]+)/)?.[1]
  useEffect(()=>{api.environment().then(setEnvironment).catch(()=>undefined)},[])
  const resetDemo=async()=>{if(!window.confirm('Reset the synthetic Acme demo to its initial state? This removes proposal and audit history.'))return;setResetting(true);try{await api.resetDemo();window.location.assign('/projects/acme-crm/recovery')}finally{setResetting(false)}}
  const nav = <>
    <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-5"><div className="grid size-9 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white">CO</div><div><div className="font-semibold text-white">ContextOS</div><div className="text-xs text-slate-400">Delivery intelligence</div></div></div>
    <nav className="p-3" aria-label="Primary navigation">
      <p className="px-3 pb-2 pt-3 text-xs font-semibold uppercase tracking-[.14em] text-slate-500">Workspace</p>
      <NavLink to="/" end onClick={() => setOpen(false)} className={({isActive}) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'}`}><BriefcaseBusiness size={18}/>Portfolio</NavLink>
      <NavLink to={currentProject?`/projects/${currentProject}`:'/'} onClick={() => setOpen(false)} className={({isActive}) => `mt-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${currentProject&&isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'}`}><FolderKanban size={18}/>Project workspace</NavLink>
      <NavLink to="/proposals" onClick={() => setOpen(false)} className={({isActive}) => `mt-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'}`}><FileCheck2 size={18}/>Recovery proposals</NavLink>
      <NavLink to="/activity" onClick={() => setOpen(false)} className={({isActive}) => `mt-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'}`}><ScrollText size={18}/>Activity and audit</NavLink>
    </nav>
    <div className="mt-auto border-t border-slate-800 p-4"><div className="flex items-start gap-2 rounded-lg bg-slate-800/70 p-3"><Activity className="mt-0.5 text-emerald-400" size={16}/><div><p className="text-xs font-medium text-slate-200">Deterministic engine</p><p className="mt-1 text-xs leading-5 text-slate-400">Schedules reflect backend calculations.</p></div></div></div>
  </>
  return <div className="min-h-screen bg-canvas">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-slate-950 lg:flex">{nav}</aside>
    {open && <div className="fixed inset-0 z-40 lg:hidden"><button aria-label="Close navigation overlay" className="absolute inset-0 bg-slate-950/40" onClick={() => setOpen(false)}/><aside className="relative flex h-full w-72 flex-col bg-slate-950">{nav}<button aria-label="Close navigation" className="absolute right-3 top-4 rounded-md p-2 text-slate-300" onClick={() => setOpen(false)}><X/></button></aside></div>}
    <div className="lg:pl-64">
      <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 py-2 backdrop-blur sm:px-6 lg:px-8"><button className="rounded-md p-2 text-slate-600 lg:hidden" aria-label="Open navigation" onClick={() => setOpen(true)}><Menu/></button><div className="hidden items-center gap-2 text-sm text-slate-500 lg:flex"><PanelLeftClose size={17}/>Portfolio operations</div><div className="flex items-center gap-2">{environment?.write_enabled&&<button disabled={resetting} onClick={resetDemo} className="hidden items-center gap-1.5 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 sm:inline-flex"><RotateCcw size={14}/>{resetting?'Resetting':'Reset demo'}</button>}<div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600">Synthetic {environment?.environment??'demo'} · {environment?.write_enabled?'Demo operator':'Read only'}</div></div></header>
      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8"><Outlet/></main>
    </div>
  </div>
}
