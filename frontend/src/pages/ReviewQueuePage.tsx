import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getReviewQueue, listTickets } from '../api/tickets'
import { ConfidenceBadge, IntentBadge } from '../components/Badge'
import { ApiError } from '../lib/client'
import type { QueueItem, TicketSummary } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: QueueItem[]; escalated: TicketSummary[] }

function QueueCard({ item }: { item: QueueItem }) {
  return (
    <Link
      to={`/tickets/${item.ticket_id}`}
      className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {item.customer_email ?? 'Unknown customer'}
          </p>
          <p className="truncate text-sm text-slate-500">
            {item.ticket_subject ?? item.subject ?? '(no subject)'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <IntentBadge intent={item.intent} />
          <ConfidenceBadge value={item.confidence} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Customer wrote
          </p>
          {/* Untrusted Customer text — rendered as text, never HTML. */}
          <p className="mt-1 line-clamp-4 whitespace-pre-wrap text-sm text-slate-700">
            {item.body ?? ''}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            AI draft
          </p>
          <p className="mt-1 line-clamp-4 whitespace-pre-wrap text-sm text-slate-700">
            {item.ai_draft ?? '(no draft)'}
          </p>
        </div>
      </div>
    </Link>
  )
}

function EscalatedCard({ ticket }: { ticket: TicketSummary }) {
  return (
    <Link
      to={`/tickets/${ticket.id}`}
      className="block rounded-2xl border border-amber-200 bg-amber-50 p-4 shadow-sm transition hover:border-amber-400 hover:shadow"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-semibold text-slate-900">
          {ticket.subject?.trim() || '(no subject)'}
        </p>
        <span className="shrink-0 rounded-full bg-amber-200 px-2 py-0.5 text-xs font-medium text-amber-900">
          {ticket.escalation_reason ?? 'escalated'}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Ticket #{ticket.id} · {ticket.status} — open to review the draft and
        reply manually.
      </p>
    </Link>
  )
}

export default function ReviewQueuePage() {
  const [state, setState] = useState<State>({ status: 'loading' })

  const load = useCallback(() => {
    let cancelled = false
    setState({ status: 'loading' })
    Promise.all([getReviewQueue(), listTickets()])
      .then(([items, tickets]) => {
        if (cancelled) return
        setState({
          status: 'ready',
          items,
          escalated: tickets.filter((t) => t.escalated),
        })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message:
            err instanceof ApiError ? err.message : 'Failed to load the queue',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  return (
    <section>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Review queue</h2>
          <p className="text-sm text-slate-500">
            Drafts awaiting review, lowest confidence first.
          </p>
        </div>
        <button
          onClick={() => load()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Refresh
        </button>
      </div>

      {state.status === 'loading' && (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading the queue…
        </p>
      )}

      {state.status === 'error' && (
        <div
          role="alert"
          className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700"
        >
          {state.message}
        </div>
      )}

      {state.status === 'ready' && state.items.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center">
          <p className="text-sm font-medium text-slate-700">
            The queue is empty
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {state.escalated.length > 0
              ? 'No drafts are awaiting quick review — but there are escalated tickets below that need human attention.'
              : 'New drafts appear here as the worker processes inbound email.'}
          </p>
        </div>
      )}

      {state.status === 'ready' && state.items.length > 0 && (
        <div className="space-y-4">
          {state.items.map((item) => (
            <QueueCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {state.status === 'ready' && state.escalated.length > 0 && (
        <div className="mt-8">
          <h3 className="text-base font-semibold text-slate-900">
            Escalated — needs human attention ({state.escalated.length})
          </h3>
          <p className="mb-3 text-sm text-slate-500">
            These Tickets were flagged by the AI (low confidence, complaints,
            or needs-human) and are excluded from the quick-review queue. Open
            one to read the thread, edit its draft, and reply.
          </p>
          <div className="space-y-3">
            {state.escalated.map((ticket) => (
              <EscalatedCard key={ticket.id} ticket={ticket} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
