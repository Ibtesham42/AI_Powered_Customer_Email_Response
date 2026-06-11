import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import * as authApi from '../api/auth'
import { refreshSession, UNAUTHORIZED_EVENT } from '../lib/client'
import { clearAccessToken, setAccessToken } from '../lib/tokenStorage'
import type { CurrentUser } from '../lib/types'
import { AuthContext, type AuthStatus } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)

  // On load there is no in-memory access token (it never persists). Try a silent
  // refresh from the httpOnly cookie to rebootstrap a session; if it succeeds,
  // fetch the current user. No cookie / expired session → unauthenticated.
  useEffect(() => {
    let cancelled = false
    refreshSession()
      .then(async (ok) => {
        if (cancelled) return
        if (!ok) {
          setStatus('unauthenticated')
          return
        }
        const me = await authApi.getMe()
        if (cancelled) return
        setUser(me)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        setUser(null)
        setStatus('unauthenticated')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // The client emits this when a refresh fails mid-session — drop to login.
  useEffect(() => {
    const handler = () => {
      setUser(null)
      setStatus('unauthenticated')
    }
    window.addEventListener(UNAUTHORIZED_EVENT, handler)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handler)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    // Login sets the refresh cookie and returns the access token (held in
    // memory only); the body's refresh_token is ignored — the cookie owns it.
    const tokens = await authApi.login({ email, password })
    setAccessToken(tokens.access_token)
    const me = await authApi.getMe()
    setUser(me)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // Best-effort server-side revocation; the local session ends regardless.
    }
    clearAccessToken()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
