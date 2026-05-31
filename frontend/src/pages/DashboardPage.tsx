import { useAuth } from '../auth/useAuth'

export default function DashboardPage() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
              AI Customer Support
            </p>
            <h1 className="text-lg font-bold text-slate-900">Agent Console</h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-600">{user?.email}</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium uppercase text-slate-500">
              {user?.role}
            </span>
            <button
              onClick={() => void logout()}
              className="rounded-lg border border-slate-300 px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            You're signed in
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            The review queue, knowledge base, mailbox, and analytics land in the
            next chunks. For now this confirms authentication and the API client
            work end to end.
          </p>
        </div>
      </main>
    </div>
  )
}
