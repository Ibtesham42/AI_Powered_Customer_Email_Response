// Types mirroring the backend Pydantic schemas (backend/models/schemas.py) and
// auth route responses (backend/routes/auth.py). Keep these in sync with the
// backend; the frontend holds no business logic, it just renders/sends these.

export interface SignupRequest {
  full_name: string
  company_name: string
  email: string
  phone: string
  password: string
  verify_password: string
  address: string
  city: string
  state: string
  country: string
  postal_code: string
}

export interface SignupResponse {
  message: string
  company_id: number
  user_id: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

export interface MessageResponse {
  message: string
}

/** The authenticated user context returned by GET /user/me. */
export interface CurrentUser {
  id: number
  email: string
  company_id: number
  role: 'owner' | 'agent'
}

interface MeResponse {
  message: string
  user: CurrentUser
}

export type { MeResponse }

export type Intent =
  | 'product_inquiry'
  | 'damaged_delivery'
  | 'refund_request'
  | 'service_inquiry'
  | 'complaint'
  | 'general_support'

export type TicketStatus = 'open' | 'pending' | 'resolved' | 'closed'

export type ReviewStatus =
  | 'awaiting_ai'
  | 'drafted'
  | 'reviewed'
  | 'sent'
  | 'not_applicable'

/** A Message as serialized by the backend (message_dict). */
export interface MessageDetail {
  id: number
  ticket_id: number
  direction: 'inbound' | 'outbound'
  subject: string | null
  body: string | null
  sender_email: string | null
  recipient_email: string | null
  review_status: ReviewStatus | null
  intent: Intent | null
  confidence: number | null
  ai_draft: string | null
  final_reply: string | null
}

/**
 * One row of GET /tickets/queue: a DRAFTED inbound Message awaiting review
 * enriched with its Ticket subject + Customer email. The backend returns these
 * lowest-confidence-first and excludes escalated Tickets.
 */
export interface QueueItem extends MessageDetail {
  ticket_subject: string | null
  customer_email: string | null
}

/** A Ticket as serialized by the backend (ticket_dict). */
export interface TicketSummary {
  id: number
  subject: string | null
  thread_id: string | null
  status: TicketStatus
  escalated: boolean
  escalation_reason: string | null
  intent: Intent | null
  customer_id: number
  assigned_to: number | null
}

export interface TicketCustomer {
  id: number
  email: string
  name: string | null
}

/** GET /tickets/{id}. */
export interface TicketDetailResponse {
  ticket: TicketSummary
  customer: TicketCustomer | null
  messages: MessageDetail[]
}

export type KbDocType = 'pdf' | 'docx' | 'csv' | 'txt' | 'json' | 'url' | 'faq'

export type KbDocStatus = 'pending' | 'processing' | 'indexed' | 'error'

/** A knowledge-base document (kb_document_dict). */
export interface KbDocument {
  id: number
  filename: string
  doc_type: KbDocType
  status: KbDocStatus
  error: string | null
  created_at: string | null
  indexed_at: string | null
}

/** Response from /data/upload, /data/url, /data/faq. */
export interface KbUploadResponse {
  message: string
  document: KbDocument
}

export type MailboxStatus = 'connected' | 'error'

/** A connected support mailbox (mailbox_dict) — never includes the credential. */
export interface Mailbox {
  id: number
  company_id: number
  email_address: string
  provider: string
  imap_host: string
  smtp_host: string
  status: MailboxStatus
  last_polled_at: string | null
}

export interface MailboxConnectRequest {
  email_address: string
  app_password: string
  imap_host: string
  smtp_host: string
}

/** GET /dashboard/stats (ticket_service.company_stats). */
export interface DashboardStats {
  tickets_total: number
  tickets_open: number
  tickets_pending: number
  tickets_resolved: number
  tickets_closed: number
  tickets_escalated: number
  review_queue: number
}
