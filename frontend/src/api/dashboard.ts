import { api } from '../lib/client'
import type { DashboardStats } from '../lib/types'

/** Company-scoped ticket counts for the overview. */
export function getStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/dashboard/stats')
}
