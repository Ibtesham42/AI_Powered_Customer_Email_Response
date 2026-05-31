import { api } from '../lib/client'
import type { QueueItem, TicketDetailResponse } from '../lib/types'

/** Inbound Messages awaiting review — lowest confidence first, non-escalated. */
export function getReviewQueue(): Promise<QueueItem[]> {
  return api.get<QueueItem[]>('/tickets/queue')
}

/** A Ticket with its Customer and full Message thread. */
export function getTicket(ticketId: number): Promise<TicketDetailResponse> {
  return api.get<TicketDetailResponse>(`/tickets/${ticketId}`)
}
