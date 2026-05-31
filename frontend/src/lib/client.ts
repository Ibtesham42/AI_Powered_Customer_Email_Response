// Typed HTTP client for the backend `/api/v1` API.
//
// - Attaches the bearer access token to authenticated requests.
// - On a 401, transparently refreshes the token once and retries; if the
//   refresh fails, clears the session and emits `UNAUTHORIZED_EVENT` so the auth
//   store can redirect to login.
// - Normalises backend error envelopes ({detail: string} or 422
//   [{loc,msg,...}]) into an `ApiError` with a human-readable message.

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from './tokenStorage'
import type { TokenResponse } from './types'

// Relative by default (dev proxy / same-origin). Set VITE_API_BASE_URL to an
// absolute origin for a separate-origin production deploy (see ADR-0004).
const API_BASE = `${import.meta.env.VITE_API_BASE_URL ?? ''}/api/v1`

/** Fired when the session can no longer be refreshed; the auth store listens. */
export const UNAUTHORIZED_EVENT = 'acs:unauthorized'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  /** Send the access token (default true). Auth endpoints pass false. */
  auth?: boolean
}

function extractMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((e) =>
          e && typeof e === 'object' && 'msg' in e
            ? String((e as { msg: unknown }).msg)
            : null,
        )
        .filter((m): m is string => m !== null)
      if (msgs.length > 0) return msgs.join('; ')
    }
  }
  return `Request failed (${status})`
}

// Dedupe concurrent refreshes: many in-flight requests share one refresh call.
let refreshInFlight: Promise<boolean> | null = null

async function doRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false
    const data = (await res.json()) as TokenResponse
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

function refreshTokens(): Promise<boolean> {
  if (refreshInFlight === null) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

async function parseBody(res: Response): Promise<unknown> {
  if (res.status === 204) return undefined
  const text = await res.text()
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  retried = false,
): Promise<T> {
  const { method = 'GET', body, auth = true } = options
  const isForm = body instanceof FormData

  const headers: Record<string, string> = {}
  // Let the browser set multipart boundaries for FormData; JSON otherwise.
  if (body !== undefined && !isForm)
    headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getAccessToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })

  if (res.status === 401 && auth && !retried) {
    const refreshed = await refreshTokens()
    if (refreshed) return request<T>(path, options, true)
    clearTokens()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new ApiError(401, 'Session expired. Please log in again.')
  }

  const parsed = await parseBody(res)
  if (!res.ok)
    throw new ApiError(res.status, extractMessage(parsed, res.status))
  return parsed as T
}

export const api = {
  get: <T>(path: string, auth = true) =>
    request<T>(path, { method: 'GET', auth }),
  post: <T>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: 'POST', body, auth }),
  put: <T>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: 'PUT', body, auth }),
  postForm: <T>(path: string, form: FormData, auth = true) =>
    request<T>(path, { method: 'POST', body: form, auth }),
}
