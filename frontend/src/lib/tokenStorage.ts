// Token persistence. The backend returns the refresh token in JSON (it does not
// set an httpOnly cookie), so the SPA must store it client-side; localStorage is
// the pragmatic choice until the backend supports cookie-based sessions. Access
// + refresh tokens only — never any other secret.

const ACCESS_KEY = 'acs.access_token'
const REFRESH_KEY = 'acs.refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_KEY, accessToken)
  localStorage.setItem(REFRESH_KEY, refreshToken)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function hasTokens(): boolean {
  return getAccessToken() !== null && getRefreshToken() !== null
}
