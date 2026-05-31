import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getTicket } from '../api/tickets'
import { EscalatedBadge, TicketStatusBadge } from '../components/Badge'
import { ReviewPanel } from '../components/ReviewPanel'
import { ApiError } from '../lib/client'
import { reviewStatusLabel } from '../lib/labels'
import type { MessageDetail, TicketDetailResponse } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: TicketDetailResponse }

function MessageBubble({ message }: { message: MessageDetail }) {
  const inbound = message.direction === 'inbound'
  return (
    <div className={inbound ? 'text-left' : 'text-right'}>
      <div
        className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
          inbound
            ? 'border border-slate-200 bg-white text-slate-800'
            : 'bg-indigo-600 text-white'
        }`}
      >
        {/* Untrusted Customer text — rendered as text, never HTML. */}
        {message.body ?? ''}
      </div>
      <p className="mt-1 text-xs text-slate-400">
        {inbound ? 'Customer' : 'Support'}
        {inbound && message.review_status
          ? ` · ${reviewStatusLabel(message.review_status)}`
          : ''}
      </p>
    </div>
  )
}

function isActionable(message: MessageDetail): boolean {
  return (
    message.direction === 'inbound' &&
    (message.review_status === 'drafted' ||
      message.review_status === 'reviewed')
  )
}

export default function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const id = Number(ticketId)
  const navigate = useNavigate()
  const [state, setState] = useState<State>({ status: 'loading' })

  const load = useCallback(() => {
    if (!Number.isFinite(id)) {
      setState({ status: 'error', message: 'Invalid ticket id' })
      return
    }
    let cancelled = false
    getTicket(id)
      .then((data) => {
        if (!cancelled) setState({ status: 'ready', data })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message:
            err instanceof ApiError ? err.message : 'Failed to load the ticket',
        })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => load(), [load])

  return (
    <section>
      <Link
        to="/"
        className="text-sm font-medium text-indigo-600 hover:underline"
      >
        ← Back to queue
      </Link>

      {state.status === 'loading' && (
        <p className="mt-4 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
          Loading the ticket…
        </p>
      )}

      {state.status === 'error' && (
        <div
          role="alert"
          className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700"
        >
          {state.message}
        </div>
      )}

      {state.status === 'ready' && (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold text-slate-900">
              {state.data.ticket.subject ?? '(no subject)'}
            </h2>
            <TicketStatusBadge status={state.data.ticket.status} />
            {state.data.ticket.escalated && (
              <EscalatedBadge reason={state.data.ticket.escalation_reason} />
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {state.data.customer?.email ?? 'Unknown customer'}
          </p>

          <div className="mt-6 space-y-4">
            {state.data.messages.map((message) => (
              <div key={message.id} className="space-y-3">
                <MessageBubble message={message} />
                {isActionable(message) && (
                  <ReviewPanel
                    message={message}
                    onChanged={load}
                    onEscalated={() => navigate('/')}
                  />
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
