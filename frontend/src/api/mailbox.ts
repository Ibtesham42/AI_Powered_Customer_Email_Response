import { api, ApiError } from '../lib/client'
import type { Mailbox, MailboxConnectRequest } from '../lib/types'

/** The Company's connected mailbox, or null if none (backend 404). */
export async function getMailbox(): Promise<Mailbox | null> {
  try {
    return await api.get<Mailbox>('/mailbox')
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

/** Verify IMAP + SMTP and store the mailbox (Owner-only). */
export function connectMailbox(
  payload: MailboxConnectRequest,
): Promise<Mailbox> {
  return api.post<Mailbox>('/mailbox/connect', payload)
}
