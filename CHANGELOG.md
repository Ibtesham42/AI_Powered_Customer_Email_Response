# Changelog

Production-hardening refactor of the AI Customer Support SaaS. Newest first;
each entry references its git commit.

## Phase 6 — Frontend: Vite + React SPA (in progress) · branch `feature/phase-6-frontend`

### Chunk 0 — adopt Vite + React (ADR-0004)
- Frontend strategy pivot: a Vite + React + TS + Tailwind SPA replaces both the
  planned Streamlit-polish phase and the Next.js phase. `docs/adr/0004`,
  roadmap Phase 6 rewrite, `frontend-engineer.md` and CLAUDE.md updated.

### Chunk 1 — scaffold
- `frontend/` — Vite 5 + React 18 + TypeScript (strict) app, Tailwind CSS v4
  (via `@tailwindcss/vite`), ESLint (flat config) + Prettier.
- `vite.config.ts` proxies `/api` and `/health` to the FastAPI backend at
  `127.0.0.1:8000` — same-origin in dev, no CORS (ADR-0004).
- Minimal landing page (`App.tsx`) with a typed `/health` connectivity check
  (loading / ok / error states). Template demo cruft removed.
- `frontend/README.md` documents the stack, dev proxy, and scripts. Verified:
  `npm run lint`, `format:check`, and `build` (incl. `tsc -b`) all clean.

## Phase 5 — AI pipeline (done) · merged to `main`

### Chunk 4 — escalation engine (completes Phase 5)
- `backend/services/escalation_service.py` — evaluates a fresh AI draft against
  the escalation rules (first match wins): `needs_human` → complaint intent →
  `repeated_replies` (thread already has `ESCALATION_MAX_REPLIES` replies out)
  → `low_confidence` (below `ESCALATION_CONFIDENCE_THRESHOLD`). Manual reject is
  the fifth rule, already handled at `/messages/{id}/reject`.
- `apply_draft_escalation` flags the Ticket via `escalate_ticket`; idempotent
  (no-op if already escalated). An escalated Ticket leaves the auto-AI review
  queue (the queue already filters `escalated == False`).
- Wired into both draft paths: the worker (`process_queue`) and
  `POST /messages/{id}/regenerate`, after `record_ai_draft`. This is where
  chunk 2's `needs_human` signal is finally consumed.
- `ticket_service.count_outbound_messages` — reply count for the repeated-replies
  rule. Thresholds in `backend/config.py` (`ESCALATION_CONFIDENCE_THRESHOLD`,
  `ESCALATION_MAX_REPLIES`), env-overridable; documented in `.env.example`.

### Chunk 3 — memory injection + Ticket summaries
- Memory injection: `ai_service.build_memory` assembles the prompt input from
  this Customer's past-Ticket summaries (budgeted to
  `PAST_SUMMARY_CHAR_BUDGET = 1500` chars) + the current Ticket's conversation
  so far + the current email. Empty sections are omitted.
- `ticket_service.list_resolved_ticket_summaries` — tenant-scoped query for a
  Customer's past summarised Tickets (newest first, capped), excluding the
  current one.
- Ticket summarisation: `ai_service.summarize_ticket` turns a Ticket's full
  thread into a 1-3 sentence internal summary (`build_summary_prompt`, which
  excludes greetings/sign-offs and sensitive data).
- `ticket_service.transition_ticket` generates that summary on the move to
  RESOLVED/CLOSED (once — never overwrites). The LLM call is best-effort:
  failures are logged and swallowed so a status transition never breaks.
- No migration: the `tickets.summary` column already exists (migration
  `76870d572c26`).

### Chunk 2 — structured generation call
- `app/llm/prompt_builder.build_structured_prompt` — one prompt that carries
  the hallucination-reduction rules and asks for a single JSON object
  `{intent, confidence, needs_human, draft}`. Allowed intents are passed in,
  so `app/` stays framework-agnostic (no backend-enum import).
- `LLMClient.generate_structured` — non-streaming Groq call with
  `response_format=json_object`; returns the raw JSON string.
- `ai_service.generate_draft` now makes the structured call and returns
  `{reply, confidence, intent, needs_human}`. Malformed output falls back to a
  safe defer-to-human result (empty draft, confidence 0, `needs_human=True`)
  rather than guessing; an empty draft is likewise forced to a human.
- `ai_service.calculate_confidence` blends retrieval similarity (primary, 0.7)
  with the LLM self-rating (secondary, 0.3) and halves the score on explicit
  non-answer phrases. No-draft cases score 0 (sorts to the top of the queue).
- `intent` is now persisted: the worker and `/messages/{id}/regenerate` pass
  `result["intent"]` to `record_ai_draft` (which already accepted it).
- `needs_human` is produced and logged now; Phase 5 chunk 4's escalation engine
  is what acts on it.

### Chunk 1 — LLM config + client hardening
- Groq model name and generation params moved out of the hardcoded
  `app/llm/llm_client.py` into `app/utils/config.py` (`Config.MODEL_NAME`,
  `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`), all env-overridable.
- `LLMClient` reads those params and applies a request `timeout` to the Groq
  client so a stalled call fails instead of hanging the worker.
- Added `get_llm_client()` — a process-level singleton. `ai_service.generate_draft`
  now calls it instead of constructing a fresh `LLMClient()` (and Groq
  connection pool) per email. No change to draft content.
- `.env.example` documents the new optional tuning vars.

## Phase 4 — RAG hardening (done) · merged to `main`

### Chunk 4 — multi-format ingestion + grounded confidence (completes Phase 4)
- URL ingestion — `POST /api/v1/data/url` fetches a web page
  (`app/rag/extract.fetch_url_text`, BeautifulSoup), ingested as a
  `doc_type=url` KbDocument.
- FAQ ingestion — `POST /api/v1/data/faq` adds a question + answer entry
  (`doc_type=faq`), stored as a text file and ingested like any other source.
- Retrieval-grounded confidence — `ai_service.calculate_confidence` now
  scores from the top chunk's cosine similarity (`rag_service.retrieve`
  returns `(chunk, distance)` pairs), replacing the keyword heuristic. The
  LLM self-rating component lands with Phase 5's structured call.
- `httpx` added as a direct dependency.

### Chunk 3 — retrieval from pgvector (multi-tenancy fix)
- `backend/services/rag_service.py` — `get_rag_context(db, query, company_id)`
  embeds the query and retrieves the nearest `kb_chunks` **filtered by
  `company_id`**, ordered by cosine distance. Tenant isolation restored.
- `ai_service.generate_draft` retrieves via `rag_service` — no longer through
  the legacy FAISS `rag_pipeline.py` and its single hardcoded `LabData` index.
- `EmbeddingModel.embed_query()`; the read path now uses the
  `get_embedding_model()` singleton — the per-email reload bug is gone.
- The FAISS modules (`rag_pipeline`, `retriever`, `vector_store`, `build_rag`,
  `preprocess`) are kept as the legacy single-tenant path for the standalone
  Streamlit apps — retired with them in Phase 7.

### Chunk 2 — in-process KB ingestion into pgvector
- `app/rag/extract.py` — plain-text extraction for PDF/DOCX/TXT/CSV/JSON
  (light cleaning only, so policy/FAQ content survives intact).
- `backend/services/kb_service.py` — `create_document` registers an upload;
  `ingest_document` (a background task) extracts → chunks → embeds → stores
  `KbChunk` rows, tracking `KbDocument.status` (pending → processing →
  indexed / error).
- `app/rag/embeddings.py` — `get_embedding_model()` process-wide singleton
  (fixes the per-call model-reload bug) + `embed_documents()`.
- `POST /api/v1/data/upload` indexes in-process via FastAPI `BackgroundTasks`
  — no more `subprocess` to `preprocess.py` / `build_rag.py`. New
  `GET /api/v1/data/documents` lists documents + index status. Upload is
  audited (`kb_document_uploaded`).
- Retrieval still uses the legacy FAISS index until chunk 3.

### Chunk 1 — pgvector foundation
- Enabled the `vector` extension; created `kb_documents` (uploaded KB
  sources) and `kb_chunks` (chunked text + 768-dim embeddings) — migration
  `4da268d4e51a`, with an HNSW cosine index on `kb_chunks.embedding`.
- `KbDocument` / `KbChunk` models; `KbDocType` / `KbDocStatus` enums.
- `pgvector` added as a dependency. Additive — no behaviour change yet; the
  write and read paths move onto pgvector in chunks 2–3.

## Phase 3 — Mailbox & ingestion · merged to `main` (`cc72072`)

### Chunk 5 — forgot / reset password (completes Phase 3)
- `password_reset_tokens` table (migration `3894e0ba0973`) — single-use,
  short-lived; only the SHA-256 token hash is stored.
- `POST /api/v1/auth/forgot-password` — always `200` (no account
  enumeration), rate-limited 5/min; emails a reset link.
- `POST /api/v1/auth/reset-password` — validates the token, sets the new
  password, consumes the token, and revokes every refresh token.
- `password_reset_service` (token lifecycle), `email_service` (Resend
  transactional email), `auth_service.revoke_all_refresh_tokens`.
- Config: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `APP_BASE_URL`,
  `RESET_TOKEN_EXPIRE_MINUTES`. `resend` added as a dependency.
- Audited: `password_reset_requested`, `password_reset_completed`.

### Chunk 4 — DB-backed AI queue
- The AI queue is no longer a JSON file — it *is* the set of inbound
  `Message`s with `review_status = awaiting_ai`.
- `email_worker.py` `process_queue()` claims Messages with
  `SELECT ... FOR UPDATE SKIP LOCKED`, one at a time; the row lock releases
  only when `record_ai_draft` commits the move to `drafted`, so concurrent
  workers never draft the same Message twice. A failed draft is logged and
  retried next cycle; `MAX_DRAFTS_PER_CYCLE` bounds one cycle.
- Removed `app/email/email_queue.py` and the `add_to_queue` enqueue call —
  creating the inbound Message *is* the enqueue.
- The legacy standalone `email_streamlit_ui.py` keeps its own
  `app/queue/email_queue.py` (untouched until Phase 7).

### Chunk 3 — worker polls each Company's mailbox
- `scripts/email_worker.py` rewritten: `poll_mailboxes()` loops over every
  connected `Mailbox`, builds a connector, fetches unread mail, ingests into
  Tickets/Messages, and records `last_polled_at` / `status` on the mailbox.
  One mailbox failing is logged and never stops the others.
- `routes/messages.py` send path now replies from the Company's *own* mailbox
  via `mailbox_service.build_connector()`, not the global `EMAIL_USER`.
- `mailbox_service.build_connector()` — the single place that turns a stored
  Mailbox into a live connector (decrypts the credential).
- Removed `INGEST_COMPANY_ID` (config + `.env.example`) and all backend use
  of the global `EMAIL_USER`/`EMAIL_PASS`. Both the worker and the send path
  now require a connected mailbox.

### Chunk 2 — mailbox connector + connect route
- `app/email/mailbox_connector.py` — `MailboxConnector` abstraction with an
  `AppPasswordConnector` (IMAP/SMTP App Password, OAuth-ready). `verify()`
  checks both IMAP and SMTP login; `MailboxError` carries a user-facing message.
- `backend/services/mailbox_service.py` — `connect_mailbox()` verifies first,
  then stores the credential encrypted (one Mailbox per Company; re-connecting
  replaces it, and a failed verify writes nothing).
- `POST /api/v1/mailbox/connect` (Owner-only) and `GET /api/v1/mailbox` —
  `routes/mailbox.py`. Connect emits a `mailbox_connected` audit event.
- `MailboxConnectRequest` schema (strips App Password whitespace);
  `mailbox_dict` serializer never exposes the credential.

### Chunk 1 — mailboxes table + credential encryption
- New `mailboxes` table (migration `0e9582994b57`) — one support mailbox per
  Company; the App Password is stored Fernet-encrypted in
  `encrypted_credential`, never plaintext (ADR-0002).
- `backend/crypto.py` — Fernet `encrypt`/`decrypt`; key from the new
  `MAILBOX_ENCRYPTION_KEY` env var, read lazily so the app still starts
  without it (fails loudly on first use instead).
- `backend/models/mailbox.py`; `MailboxProvider` / `MailboxStatus` enums.
- `cryptography` pinned as a direct dependency.

## Phase 2 — Domain model · merged to `main` (`a4d120c`)

### Chunk 4 — audit logging
- `backend/services/audit_service.py` — `record()` writes one `AuditLog` row.
  Audit failures are logged (`logger.exception`) and swallowed, then the
  session is rolled back, so a broken audit write never breaks the action it
  records.
- Events emitted: `signup`, `login`, `login_failed`, `logout` (`routes/auth.py`)
  and `message_sent`, `draft_rejected` (`routes/messages.py`). Routes gained a
  `Request` param so the client IP is captured.
- No schema change — `audit_logs` was created in Chunk 1 (`76870d572c26`).

### Chunk 3f — drop the legacy emails path (completes Chunk 3)
- Deleted `routes/email.py`, `models/email.py`, and the legacy `ai_service`
  functions (`generate_email_reply`, `get_thread_history`).
- Removed the `email` router from `main.py` and the `Email` model from
  `alembic/env.py`.
- Migration `7d78ba51b1e8` drops the (empty) `emails` table.

### Chunk 3e — re-point the Streamlit dashboard
- `dashboard_app.py` now drives `/tickets/queue`, `/tickets/{id}` and
  `/messages/{id}/{draft,send,regenerate,reject}`, plus the new
  `/dashboard/stats` keys. Per-item actions: Send / Regenerate / Reject.

### Chunk 3d — dashboard stats from tickets · `95cead9`
- `routes/dashboard.py` `/stats` now reports Ticket counts (by status,
  escalated, review-queue depth) via `ticket_service.company_stats`,
  replacing the `emails`-table counts.

### Chunk 3c — worker ingests into the domain model · `3069729`
- `email_worker.py` rewritten: ingests email via `ticket_service`
  (`find_or_open_ticket` threads replies by In-Reply-To and reopens
  resolved/closed Tickets), keyed by a new `INGEST_COMPANY_ID` config var.
- Worker converted to structured logging with an error-resilient poll loop.

### Chunk 3b — ticket/message routes · `dc1d5be`
- `routes/tickets.py` (review queue, list, ticket detail) + `routes/messages.py`
  (regenerate / edit / approve / reject / send) — thin over the services.
- `backend/serializers.py`; `InvalidTransitionError` → HTTP 409 exception
  handler in `main.py`.

### Chunk 3a — Message-based AI draft generation · `5f5eb9b`
- `ai_service.generate_draft` + `get_ticket_history`;
  `ticket_service.record_ai_draft`.

### Chunk 2 — state machines + service layer · `0660ee0`
- `backend/services/state_machine.py` — ticket-lifecycle and message-review
  transition graphs with `InvalidTransitionError` validation.
- `backend/services/ticket_service.py` — tenant-scoped domain operations for
  Customer/Ticket/Message (every query filtered by `company_id`).

### Chunk 1 — Customer/Ticket/Message domain model · `dbd716e`
- New models: `Customer`, `Ticket`, `Message`, `AuditLog`; `models/enums.py`
  StrEnum value sets.
- Migration `76870d572c26` — creates `customers`, `tickets`, `messages`,
  `audit_logs` (additive; legacy `emails` untouched).

## Phase 1 — Database & auth · merged to `main` (`37e0ec9`)

### Chunk 4 — Postgres cutover · `37e0ec9`
- `DATABASE_URL` env-driven; switched to Neon managed Postgres.
- Retired `Base.metadata.create_all` — schema is Alembic-only.
- Added `psycopg2-binary`; `pool_pre_ping` for cloud connections.

### Chunk 3 — rate limiting, RBAC, versioning · `6ed5f7a`
- slowapi rate limiting (signup 5/min, login 10/min).
- `require_owner` RBAC dependency (applied to `/data/upload`).
- All feature routes moved under `/api/v1`.

### Chunk 2 — access + refresh tokens · `176d1bb`
- `refresh_tokens` table (migration `fd095f9aa6c3`); tokens SHA-256 hashed.
- `/auth/refresh` (rotation) and `/auth/logout` (revocation).

### Chunk 1 — data model + signup hardening · `9218e78`
- `Company` address fields; `User` `full_name`/`phone`/timestamps
  (migration `3d3e063b9932`).
- Every signup creates a new Company (signer = Owner) — closes the
  join-by-name tenant-isolation hole. Pydantic-validated signup.

## Phase 0 — Safety & cleanup + planning · merged to `main` (`b662ed9`)
- `SECRET_KEY` moved to env with startup fail-fast (`backend/config.py`).
- Deleted dead `backend/routes/ai.py`; fixed `main.py`.
- Structured logging; ruff/black/mypy config; Alembic baseline migration.
- Planning docs: `CONTEXT.md`, `docs/adr/0001-0003`, `SYSTEM_ARCHITECTURE.md`,
  `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md`, `IMPLEMENTATION_ROADMAP.md`,
  `.claude/agents/*`.

## Pre-refactor
- `2a1317e` backend auth system · `04709ba` initial RAG + review + SMTP build.
