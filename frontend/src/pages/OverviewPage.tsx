import { type ReactNode, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getStats } from '../api/dashboard'
import { ApiError } from '../lib/client'
import type { DashboardStats } from '../lib/types'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; stats: DashboardStats }

function StatCard({
  label,
  value,
  tone = 'default',
  to,
}: {
  label: string
  value: number
  tone?: 'default' | 'accent' | 'danger'
  to?: string
}) {
  const toneClasses =
    tone === 'accent'
      ? 'border-indigo-200 bg-indigo-50'
      : tone === 'danger'
        ? 'border-rose-200 bg-rose-50'
        : 'border-slate-200 bg-white'
  const valueClasses =
    tone === 'accent'
      ? 'text-indigo-700'
      : tone === 'danger'
        ? 'text-rose-700'
        : 'text-slate-900'

  const inner: ReactNode = (
    <div className={`rounded-2xl border p-5 shadow-sm ${toneClasses}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={`mt-2 text-3xl font-bold ${valueClasses}`}>{value}</p>
    </div>
  )

  return to ? (
    <Link to={to} className="block transition hover:opacity-90">
      {inner}
    </Link>
  ) : (
    inner
  )
}

export default function OverviewPage() {
  const [state, setState] = useState<State>({ status: 'loading' })

  const load = useCallback(() => {
    let cancelled = false
    setState({ status: 'loading' })
    getStats()
      .then((stats) => {
        if (!cancelled) setState({ status: 'ready', stats })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message:
            err instanceof ApiError ? err.message : 'Failed to load stats',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Overview</h2>
          <p className="text-sm text-slate-500">
            Your support workload at a glance.
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
          Loading stats…
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

      {state.status === 'ready' && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard
              label="Awaiting review"
              value={state.stats.review_queue}
              tone="accent"
              to="/"
            />
            <StatCard
              label="Escalated"
              value={state.stats.tickets_escalated}
              tone="danger"
            />
            <StatCard label="Total tickets" value={state.stats.tickets_total} />
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-900">
              Tickets by status
            </h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Open" value={state.stats.tickets_open} />
              <StatCard label="Pending" value={state.stats.tickets_pending} />
              <StatCard label="Resolved" value={state.stats.tickets_resolved} />
              <StatCard label="Closed" value={state.stats.tickets_closed} />
            </div>
          </div>
        </>
      )}
    </section>
  )
}
