// Auth endpoint wrappers. Public endpoints (login/signup/forgot/reset) pass
// auth=false; getMe is authenticated.

import { api } from '../lib/client'
import type {
  CurrentUser,
  ForgotPasswordRequest,
  LoginRequest,
  MeResponse,
  MessageResponse,
  ResetPasswordRequest,
  SignupRequest,
  SignupResponse,
  TokenResponse,
} from '../lib/types'

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return api.post<TokenResponse>('/auth/login', payload, false)
}

export function signup(payload: SignupRequest): Promise<SignupResponse> {
  return api.post<SignupResponse>('/auth/signup', payload, false)
}

export function logout(refreshToken: string): Promise<MessageResponse> {
  return api.post<MessageResponse>(
    '/auth/logout',
    { refresh_token: refreshToken },
    false,
  )
}

export function forgotPassword(
  payload: ForgotPasswordRequest,
): Promise<MessageResponse> {
  return api.post<MessageResponse>('/auth/forgot-password', payload, false)
}

export function resetPassword(
  payload: ResetPasswordRequest,
): Promise<MessageResponse> {
  return api.post<MessageResponse>('/auth/reset-password', payload, false)
}

export async function getMe(): Promise<CurrentUser> {
  const res = await api.get<MeResponse>('/user/me')
  return res.user
}
