import type {
  Intent,
  KbDocStatus,
  MailboxStatus,
  TicketStatus,
} from '../lib/types'

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

const TICKET_STATUS_TONE: Record<TicketStatus, string> = {
  open: 'bg-sky-100 text-sky-700',
  pending: 'bg-amber-100 text-amber-700',
  resolved: 'bg-emerald-100 text-emerald-700',
  closed: 'bg-slate-100 text-slate-600',
}

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${TICKET_STATUS_TONE[status]}`}
    >
      {status}
    </span>
  )
}

export function EscalatedBadge({ reason }: { reason: string | null }) {
  return (
    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
      Escalated{reason ? `: ${reason.replace(/_/g, ' ')}` : ''}
    </span>
  )
}

const KB_STATUS_TONE: Record<KbDocStatus, string> = {
  pending: 'bg-slate-100 text-slate-600',
  processing: 'bg-amber-100 text-amber-700',
  indexed: 'bg-emerald-100 text-emerald-700',
  error: 'bg-rose-100 text-rose-700',
}

export function KbStatusBadge({ status }: { status: KbDocStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${KB_STATUS_TONE[status]}`}
    >
      {status}
    </span>
  )
}

export function MailboxStatusBadge({ status }: { status: MailboxStatus }) {
  const tone =
    status === 'connected'
      ? 'bg-emerald-100 text-emerald-700'
      : 'bg-rose-100 text-rose-700'
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${tone}`}
    >
      {status}
    </span>
  )
}
