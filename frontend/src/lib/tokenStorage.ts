// Access-token storage (audit H1). The token lives in memory only — never in
// localStorage — so an XSS payload can't exfiltrate a persisted credential, and
// it is gone the moment the tab closes. The refresh token is not stored here at
// all: it rides in an httpOnly cookie the browser sends to /api/v1/auth/* and
// JavaScript can't read. On a fresh load the SPA silently refreshes (the cookie)
// to mint a new in-memory access token — see AuthProvider.

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}

export function hasAccessToken(): boolean {
  return accessToken !== null
}
