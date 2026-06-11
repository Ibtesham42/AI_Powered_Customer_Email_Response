import { api } from '../lib/client'
import type {
  QueueItem,
  TicketDetailResponse,
  TicketSummary,
} from '../lib/types'

/** Inbound Messages awaiting review — lowest confidence first, non-escalated. */
export function getReviewQueue(): Promise<QueueItem[]> {
  return api.get<QueueItem[]>('/tickets/queue')
}

/** All of the Company's Tickets (incl. escalated — the queue excludes those). */
export function listTickets(): Promise<TicketSummary[]> {
  return api.get<TicketSummary[]>('/tickets')
}

/** A Ticket with its Customer and full Message thread. */
export function getTicket(ticketId: number): Promise<TicketDetailResponse> {
  return api.get<TicketDetailResponse>(`/tickets/${ticketId}`)
}
