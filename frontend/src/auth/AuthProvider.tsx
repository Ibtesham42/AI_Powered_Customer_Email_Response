import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import * as authApi from '../api/auth'
import { UNAUTHORIZED_EVENT } from '../lib/client'
import {
  clearTokens,
  getRefreshToken,
  hasTokens,
  setTokens,
} from '../lib/tokenStorage'
import type { CurrentUser } from '../lib/types'
import { AuthContext, type AuthStatus } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)

  // On load, validate any stored session by fetching the current user. The
  // client transparently refreshes the access token if it has expired.
  useEffect(() => {
    if (!hasTokens()) {
      setStatus('unauthenticated')
      return
    }
    let cancelled = false
    authApi
      .getMe()
      .then((me) => {
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
    const tokens = await authApi.login({ email, password })
    setTokens(tokens.access_token, tokens.refresh_token)
    const me = await authApi.getMe()
    setUser(me)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken()
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken)
      } catch {
        // Best-effort server-side revocation; the local session ends regardless.
      }
    }
    clearTokens()
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
