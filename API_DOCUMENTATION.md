# API Documentation

Target REST API. All routes are versioned under `/api/v1`. All responses are
JSON. All non-auth routes require `Authorization: Bearer <access_token>` and
are automatically scoped to the caller's Company.

Legend: **[now]** exists today (possibly under a different path) ·
**[new]** to be built · **[change]** exists but must change ·
**[done]** built in this refactor.

> Build status is updated per chunk. All feature routes are now served under
> `/api/v1`; `/` and `/health` stay unversioned.

## Conventions

- **Auth**: Bearer access token. Expired access token → `401`; client uses the
  refresh token to get a new one.
- **Errors**: consistent envelope — `{ "error": { "code": "...",
  "message": "...", "details": {...} } }`.
- **Tenant scope**: `company_id` is taken from the token, never from the
  request body or query. Routes never accept a `company_id` parameter.
- **RBAC**: routes marked *(Owner)* require the `owner` role.
- **Pagination**: list endpoints accept `?limit=&cursor=`.

## Auth — `/api/v1/auth`

| Method | Path | Notes |
|---|---|---|
| POST | `/signup` | **[done]** Creates a new Company; caller becomes its Owner. Body: full_name, company_name, email, phone, password, verify_password, address, city, state, country, postal_code (Pydantic-validated). Returns `{company_id, user_id}`. Rate limited (5/min). |
| POST | `/login` | **[done]** Returns `access_token` + `refresh_token`. Generic error message, no account enumeration. Rate limited (10/min). |
| POST | `/refresh` | **[done]** Exchange a refresh token for a new access token; rotates the refresh token (the old one is revoked). |
| POST | `/logout` | **[done]** Revoke the refresh token. Idempotent. |
| POST | `/forgot-password` | **[done]** Body: email. Emails a reset link via Resend. Rate-limited 5/min. Always returns `200` (no account enumeration). |
| POST | `/reset-password` | **[done]** Body: reset token + new password (≥ 8 chars). Consumes the token; revokes all the user's refresh tokens. Rate-limited 10/min. |
| GET  | `/me` | **[now]** Current User + Company context. Now at `/api/v1/user/me`. |

## Company & users — `/api/v1/company`

| Method | Path | Notes |
|---|---|---|
| GET | `/` | **[new]** Company profile + address. |
| PATCH | `/` | **[new]** *(Owner)* Update Company profile. |
| GET | `/users` | **[new]** List Users in the Company. |

## Mailbox — `/api/v1/mailbox`

| Method | Path | Notes |
|---|---|---|
| GET | `/` | **[done]** Connection status (never returns the credential). `404` if none connected. |
| POST | `/connect` | **[done]** *(Owner)* Body: email_address, app_password, optional imap_host/smtp_host. Verifies IMAP **and** SMTP login before saving; stores the App Password Fernet-encrypted. Audited (`mailbox_connected`). |
| POST | `/test` | **[new]** Re-verify the stored connection. |
| DELETE | `/` | **[new]** *(Owner)* Disconnect the mailbox. |

## Knowledge base — `/api/v1/kb`

| Method | Path | Notes |
|---|---|---|
| GET | `/documents` | **[new]** List KB documents + index status. |
| POST | `/documents` | **[change]** Upload a file (PDF/DOCX/CSV/TXT). Was `/data/upload`; replace the synchronous `subprocess` train with a background index task. |
| POST | `/documents/url` | **[new]** Ingest website/page content by URL. |
| POST | `/documents/faq` | **[new]** Add an FAQ entry (question + answer). |
| DELETE | `/documents/{id}` | **[new]** Remove a document and its chunks. |
| POST | `/search` | **[new]** Debug: semantic search over this Company's KB. |

## Tickets — `/api/v1/tickets`

| Method | Path | Notes |
|---|---|---|
| GET | `/` | **[done]** List Tickets. Filter: `status` (other filters deferred). |
| GET | `/queue` | **[done]** Review queue: DRAFTED Messages on non-escalated Tickets, lowest confidence first, enriched with ticket subject + customer email. Replaces `/email/todo`. |
| GET | `/{id}` | **[done]** Ticket + Customer + full Message thread. (Memory summaries: Phase 5.) |
| PATCH | `/{id}` | **[new]** Update status / assignee. |
| POST | `/{id}/escalate` | **[new]** Manually escalate. |
| POST | `/{id}/resolve` | **[new]** Mark resolved (triggers summary generation). |

## Messages & review — `/api/v1/messages`

| Method | Path | Notes |
|---|---|---|
| POST | `/{id}/regenerate` | **[done]** Re-run the AI Draft for an inbound Message. |
| PUT | `/{id}/draft` | **[done]** Edit/rewrite the Draft (body `{text}`) → `review_status = reviewed`. |
| POST | `/{id}/approve` | **[done]** Accept the Draft as-is → `reviewed`. |
| POST | `/{id}/reject` | **[done]** Discard the Draft → escalate the Ticket. |
| POST | `/{id}/send` | **[done]** Send the reviewed reply over SMTP → `sent`; opens an outbound Message; Ticket → `pending`. |

## Dashboard & analytics — `/api/v1/dashboard`

| Method | Path | Notes |
|---|---|---|
| GET | `/stats` | **[done]** Ticket counts by status, escalated count, review-queue depth. Tenant-scoped. |
| GET | `/analytics` | **[new]** Time-series: volume, avg confidence, intent breakdown, resolution time. |

## Customers — `/api/v1/customers`

| Method | Path | Notes |
|---|---|---|
| GET | `/` | **[new]** List Customers. |
| GET | `/{id}` | **[new]** Customer + all their Tickets (the conversation history view). |

## System

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | **[now]** Liveness. |
| GET | `/health/ready` | **[new]** Readiness — DB + dependencies reachable. |

## Routes to remove

- `backend/routes/ai.py` — dead/broken (`RAGPipeline(user_id=...)`, status
  `"replied"`). Delete; `email.py`/`messages` already cover it.
- `email_queue.json` and its helpers — **[done]** removed in Phase 3 chunk 4;
  the queue is now `messages WHERE review_status = awaiting_ai`.
