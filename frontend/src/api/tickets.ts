import { api } from '../lib/client'
import type { QueueItem } from '../lib/types'

/** Inbound Messages awaiting review — lowest confidence first, non-escalated. */
export function getReviewQueue(): Promise<QueueItem[]> {
  return api.get<QueueItem[]>('/tickets/queue')
}
