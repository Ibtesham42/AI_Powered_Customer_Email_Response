import { useEffect, useState } from 'react'

type HealthState =
  | { status: 'loading' }
  | { status: 'ok' }
  | { status: 'error'; message: string }

/**
 * Probe the backend `/health` endpoint (proxied to FastAPI in dev). A scaffold
 * smoke test that the SPA and backend can talk; replaced by real data fetching
 * in later chunks.
 */
function useBackendHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    fetch('/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<{ status?: string }>
      })
      .then((data) => {
        if (cancelled) return
        setState(
          data.status === 'ok'
            ? { status: 'ok' }
            : { status: 'error', message: 'unexpected response' },
        )
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: err instanceof Error ? err.message : 'unreachable',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}

function BackendBadge({ health }: { health: HealthState }) {
  const map = {
    loading: { dot: 'bg-amber-400', label: 'Checking backend…' },
    ok: { dot: 'bg-emerald-500', label: 'Backend connected' },
    error: { dot: 'bg-rose-500', label: 'Backend unreachable' },
  } as const
  const { dot, label } = map[health.status]
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-700">
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden />
      <span>{label}</span>
      {health.status === 'error' && (
        <span className="text-slate-400">({health.message})</span>
      )}
    </div>
  )
}

function App() {
  const health = useBackendHealth()

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <main className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
          AI Customer Support
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          Agent Console
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Vite + React + TypeScript frontend (scaffold). The review queue, KB,
          and mailbox panels land in the next chunks.
        </p>
        <div className="mt-6">
          <BackendBadge health={health} />
        </div>
      </main>
    </div>
  )
}

export default App
