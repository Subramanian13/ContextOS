import { AlertTriangle, CheckCircle2, CircleAlert } from 'lucide-react'
import type { RiskStatus } from '../types'

const labels: Record<RiskStatus, string> = { on_track: 'On track', at_risk: 'At risk', off_track: 'Off track' }
const styles: Record<RiskStatus, string> = { on_track: 'bg-emerald-50 text-emerald-700', at_risk: 'bg-amber-50 text-amber-800', off_track: 'bg-red-50 text-red-700' }

export function Status({ value }: { value: RiskStatus }) {
  const Icon = value === 'on_track' ? CheckCircle2 : value === 'at_risk' ? AlertTriangle : CircleAlert
  return <span className={`status-pill gap-1.5 ${styles[value]}`}><Icon size={14} aria-hidden="true" />{labels[value]}</span>
}
