import { api } from '../lib/client'
import type { MessageDetail } from '../lib/types'

/** Re-run the AI draft for an inbound Message (stays DRAFTED). */
export function regenerateDraft(messageId: number): Promise<MessageDetail> {
  return api.post<MessageDetail>(`/messages/${messageId}/regenerate`)
}

/** Save an edited/rewritten reply and mark the Message REVIEWED. */
export function saveDraft(
  messageId: number,
  text: string,
): Promise<MessageDetail> {
  return api.put<MessageDetail>(`/messages/${messageId}/draft`, { text })
}

/** Accept the AI draft unchanged and mark the Message REVIEWED. */
export function approveDraft(messageId: number): Promise<MessageDetail> {
  return api.post<MessageDetail>(`/messages/${messageId}/approve`)
}

/** Reject the draft — escalates the Ticket for manual handling. */
export function rejectDraft(
  messageId: number,
  reason?: string,
): Promise<{ message: string; ticket_id: number }> {
  return api.post(`/messages/${messageId}/reject`, { reason: reason ?? null })
}

/** Send the reviewed reply to the Customer (requires REVIEWED). */
export function sendReply(
  messageId: number,
): Promise<{ message: string; message_id: number }> {
  return api.post(`/messages/${messageId}/send`)
}
