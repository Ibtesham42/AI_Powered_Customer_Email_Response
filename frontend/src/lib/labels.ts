import type { ReviewStatus } from './types'

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  awaiting_ai: 'Awaiting AI',
  drafted: 'Drafted',
  reviewed: 'Reviewed',
  sent: 'Sent',
  not_applicable: '—',
}

export function reviewStatusLabel(status: ReviewStatus | null): string {
  return status ? REVIEW_STATUS_LABELS[status] : '—'
}
