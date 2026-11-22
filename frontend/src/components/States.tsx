import { AlertCircle, LoaderCircle } from 'lucide-react'

export function LoadingState({ label = 'Loading project data' }: { label?: string }) {
  return <div className="panel flex min-h-56 items-center justify-center gap-3 text-slate-600" role="status"><LoaderCircle className="animate-spin" size={20} />{label}</div>
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="panel flex min-h-56 flex-col items-center justify-center gap-3 px-6 text-center" role="alert"><AlertCircle className="text-red-600" /><div><p className="font-semibold text-ink">We couldn’t load this view</p><p className="mt-1 text-sm text-slate-600">{message}</p></div>{retry && <button className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white" onClick={retry}>Try again</button>}</div>
}
