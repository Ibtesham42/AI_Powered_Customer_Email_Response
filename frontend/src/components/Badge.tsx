import type { Intent } from '../lib/types'

const INTENT_LABELS: Record<Intent, string> = {
  product_inquiry: 'Product inquiry',
  damaged_delivery: 'Damaged delivery',
  refund_request: 'Refund request',
  service_inquiry: 'Service inquiry',
  complaint: 'Complaint',
  general_support: 'General support',
}

export function ConfidenceBadge({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
        No score
      </span>
    )
  }
  // Low confidence is the signal a reviewer most needs to see.
  const tone =
    value >= 70
      ? 'bg-emerald-100 text-emerald-700'
      : value >= 40
        ? 'bg-amber-100 text-amber-700'
        : 'bg-rose-100 text-rose-700'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${tone}`}>
      {value}% confident
    </span>
  )
}

export function IntentBadge({ intent }: { intent: Intent | null }) {
  if (intent === null) return null
  const tone =
    intent === 'complaint'
      ? 'bg-rose-100 text-rose-700'
      : 'bg-slate-100 text-slate-600'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {INTENT_LABELS[intent]}
    </span>
  )
}
