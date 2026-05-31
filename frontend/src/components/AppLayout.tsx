import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/useAuth'

const NAV = [{ to: '/', label: 'Review queue', end: true }]

export function AppLayout() {
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
        <nav className="mx-auto flex max-w-5xl gap-1 px-6">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
