# Changelog

Production-hardening refactor of the AI Customer Support SaaS. Newest first;
each entry references its git commit.

## Phase 7 — Production hardening (in progress) · branch `feature/phase-7-hardening`

Closing the Critical + High blockers from the production-readiness audit.

### Chunk 6 (C2) — deployment & runtime hardening
Built collaboratively by the devops / backend / database / security specialist
agents (design → parallel implement → security review → integrate).
- **Containers**: one shared multi-stage `Dockerfile` (`python:3.12-slim`,
  non-root `appuser`) for the `api`, `worker`, and `migrate` processes — they
  differ only by `command` (the Cloud Run pattern). `.dockerignore` keeps the
  committed `venv/`, `.env*`, `data/`, `frontend/`, and `tests/` out of the image.
- **Compose** (`docker-compose.yml`): `db` (`pgvector/pgvector:pg16`), `redis`,
  a one-shot `migrate` (`alembic upgrade head`, `restart: "no"`) that `api` and
  `worker` gate on via `depends_on … service_completed_successfully`, plus DB
  `pg_isready` / redis healthchecks and restart policies. Schema is applied by
  the migrate step, never on app startup. Labelled clearly as non-production.
- **Worker resilience** (`scripts/email_worker.py`): SIGTERM/SIGINT graceful
  shutdown (finishes the current cycle, no mid-draft kill) and a top-level crash
  guard with backoff so a hard failure (e.g. DB down at `SessionLocal()`)
  self-heals instead of crashing the process.
- **Readiness probe**: `GET /health/ready` runs a cheap engine-level `SELECT 1`
  and returns 503 if the DB is unreachable (leaks no error detail); liveness
  `GET /health` stays DB-free so a DB blip never restarts a healthy container.
- **Rate limiting**: `Limiter` now uses Redis when `RATELIMIT_STORAGE_URI` /
  `REDIS_URL` is set; **production refuses to start without it** (an in-memory
  fallback would not hold across instances — security review H1), and dev warns.
- **DB pool**: `backend/database.py` pool params (`DB_POOL_SIZE` /
  `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE`) are env-tunable for Postgres only; the
  SQLite test path is untouched. Worker runs a smaller pool (2/2).
- **CI** (`.github/workflows/ci.yml`): GitHub Actions on push/PR — `pytest`
  (SQLite suite) blocking; `ruff` / `black` / `mypy` / `pip-audit` non-blocking
  (pre-existing format drift + not-yet-mypy-clean; baseline cleanup is a tracked
  follow-up). Includes a commented Postgres+pgvector integration job for the
  deferred RAG-scoping/audit tests.
- **Docs**: `docs/runbooks/deployment.md` (local compose, migrate-as-deploy-step
  + Cloud Run analogue, health/readiness→probe mapping, prod env vars, and the
  out-of-scope hardening follow-ups). `.env.example` gains the rate-limit + DB
  pool vars. `requirements.txt` adds `redis==5.0.8`.
- Security review (read-only): no Critical; H1 fixed in-chunk; `/health/ready`
  verified non-leaking; remaining items (digest-pinned images, image CVE
  scanning, least-privilege runtime role) recorded as follow-ups.

### Chunk 5 (H1) — token transport hardening
- Refresh token now rides in an **httpOnly + Secure + SameSite** cookie scoped
  to `/api/v1/auth` (`backend/auth/cookies.py`), keeping it off the SPA's
  JavaScript (closes the localStorage XSS-exfiltration vector). `/refresh` +
  `/logout` read the token **cookie-first with a body fallback** — browser
  clients send the cookie and no body; non-browser clients (legacy Streamlit,
  tests, future mobile) still pass `refresh_token` in the body.
  `RefreshTokenRequest.refresh_token` is now optional.
- SPA: access token held **in memory only** (`tokenStorage.ts` — no
  localStorage); `client.ts` sends `credentials:'include'`, refreshes via the
  cookie with no body, and exposes `refreshSession`; `AuthProvider` silently
  re-bootstraps the session from the cookie on load (the in-memory token never
  survives a reload). `logout()` drops its argument (server reads the cookie).
- **Security-headers middleware** (`main.py`): `X-Content-Type-Options=nosniff`,
  `X-Frame-Options=DENY`, `Referrer-Policy=no-referrer`, and
  `Strict-Transport-Security` in production. CORS `allow_credentials=True` so the
  cookie flows on a separate-origin deploy (explicit origins required).
- New config: `ENVIRONMENT` (production tightens cookie-Secure + HSTS) and
  `COOKIE_SECURE` / `COOKIE_SAMESITE` / `COOKIE_DOMAIN` / `REFRESH_COOKIE_NAME`;
  documented in `.env.example`. Also corrected the stale
  `ACCESS_TOKEN_EXPIRE_MINUTES=480` example to `30` (matches the H2 default).
- `tests/test_auth.py` (+4): login sets the httpOnly cookie, cookie-only
  refresh rotates, cookie logout revokes + expires, and security headers present;
  the body-path rotation/logout tests now clear the jar to isolate that path.
  **63 green.**

### Chunk 4 (H2) — short access-token TTL + real revocation
- `users.token_version` (migration `a1b2c3d4e5f6`, `server_default="1"`). The
  access-token JWT now carries `token_version`; `get_current_user` rejects a
  token whose version ≠ the user's current one (401). The check is free — the
  dependency already loads the user row.
- `auth_service.revoke_all_sessions` bumps `token_version` (kills outstanding
  **access** tokens) **and** revokes all refresh tokens. Wired into a new
  `POST /auth/logout-all` (sign out everywhere) and into password reset (so a
  reset truly ends every session, access included).
- `ACCESS_TOKEN_EXPIRE_MINUTES` default 480 → **30** (the SPA refreshes
  transparently; the legacy Streamlit dashboard re-logs-in on expiry).
- `tests/test_token_revocation.py` (4): logout-all invalidates the access token,
  an out-of-band version bump revokes it, password reset revokes then re-login
  works, and a normal refresh keeps the token valid.

### Chunk 3 (H3) — mailbox encryption key: fail-fast + refuse-without-key
- Startup self-check (`crypto.validate_at_startup`, called from `main.py`): an
  **invalid** key always aborts startup; a **missing** key aborts only when the
  new `MAILBOX_ENCRYPTION_REQUIRED` flag is set, else the app starts with mailbox
  features disabled and logs a warning.
- Mailbox features **refuse** without a usable key: `connect_mailbox` and
  `build_connector` call `crypto.require_configured()` first (before any network
  work / before `decrypt`); `POST /mailbox/connect` maps the failure to **503**
  rather than storing plaintext or 500-ing.
- `crypto.is_configured()` / `require_configured()` helpers added.
- Runbook `docs/runbooks/mailbox-encryption-key.md`: key custody/backup,
  recovery when lost, and an offline re-encryption **rotation** procedure (with
  a ready-to-run script); `.env.example` documents `MAILBOX_ENCRYPTION_REQUIRED`.
- `tests/test_mailbox_key.py`: missing / invalid / valid key + the connect route
  returning 503 without a key (4 tests).

### Chunk 2 (H4) — SSRF guard on URL knowledge-base ingestion
- `app/rag/url_guard.py` — `validate_public_url`: allows only http/https and
  only hosts that resolve exclusively to public IPs; rejects loopback, private,
  link-local (incl. the `169.254.169.254` cloud-metadata endpoint), reserved,
  multicast, unspecified, and IPv4-mapped-IPv6 equivalents (`UnsafeUrlError`).
- `fetch_url_text` now validates before fetching and follows redirects manually
  with `follow_redirects=False`, re-validating every hop (capped at 5) — a
  redirect can't bounce to an internal address.
- `POST /api/v1/data/url` validates up front and returns 400 on an unsafe URL
  (the background fetch re-validates as defence in depth).
- 16 tests (`tests/test_url_guard.py`): public allowed; loopback/private/
  link-local/metadata/IPv6-loopback/unspecified rejected; non-http(s) schemes
  rejected; and the route returns 400 for the metadata IP.

### Chunk 1 (C1) — test harness + tenancy/auth safety net
- `pytest` + `pytest-asyncio` added (`requirements-dev.txt`, `pyproject.toml`
  `[tool.pytest.ini_options]` with `asyncio_mode=auto`). Fixes the broken
  `TestClient` (httpx 0.28) by driving routes over `httpx.ASGITransport`.
- `tests/conftest.py`: in-memory SQLite DB via `StaticPool`, `get_db` override,
  async client fixture; excludes the Postgres-only `kb_chunks` (pgvector) and
  `audit_logs` (JSONB) tables; disables the in-memory rate limiter for tests.
- **35 tests, all passing:** state machine (transitions, valid + invalid),
  escalation engine (rule priority/threshold/idempotency), AI confidence blend +
  intent/confidence coercion + structured-output parse paths (valid/malformed/
  empty), auth flow (signup/login/me/refresh-rotation/logout), and **tenant
  isolation** (Company B gets 404/empty on A's ticket, queue, message action,
  mailbox, and KB documents).
- Out of scope here (need a Postgres+pgvector DB → CI in chunk 6): RAG retrieval
  scoping and audit-log assertions.

## Phase 6 — Frontend: Vite + React SPA (done) · merged to `main`

### Chunk 7 (prep) — production CORS + API base URL
- Backend: configurable `CORS_ORIGINS` (`backend/config.py`) + `CORSMiddleware`
  (`backend/main.py`), so the built SPA can call the API from a separate origin
  in production (dev still uses the Vite proxy, same-origin). Verified: an
  allowed origin gets `access-control-allow-origin` and a 200 preflight.
- Frontend: the API client base URL is now `VITE_API_BASE_URL` + `/api/v1`,
  defaulting to relative (dev proxy / same-origin). `frontend/.env.example` +
  a README "Production build & deploy" section.
- **Streamlit retirement is intentionally deferred** to a live end-to-end test
  (login → queue → review → send) against a real DB — held this session because
  Neon DNS was unavailable in the sandbox. `dashboard_app.py` stays the working
  UI until then.

### Chunk 6 — analytics / overview
- `OverviewPage` (`/overview`): `GET /dashboard/stats` rendered as stat cards —
  awaiting-review depth (links to the queue), escalated count, total, and the
  open/pending/resolved/closed breakdown. Loading/error states + refresh.
- `api/dashboard.ts` + `DashboardStats` type; nav item added to `AppLayout`.
- Verified: lint, strict build, proxy auth-gating on `/dashboard/stats`.

### Chunk 5 — knowledge base + mailbox panels
- `KnowledgeBasePage` (`/knowledge-base`): lists `GET /data/documents` with
  per-document status badges (pending/processing/indexed/error + error text),
  plus an owner-only uploader with File / URL / FAQ modes (`/data/upload`,
  `/data/url`, `/data/faq`). Refetches the list on success.
- `MailboxPage` (`/mailbox`): shows the connected mailbox (`GET /mailbox`,
  treating 404 as "none") with a status badge, and an owner-only connect form
  (`POST /mailbox/connect`, IMAP/SMTP defaults). Agents see read-only views +
  an owner-only notice (RBAC for UX; the backend is the real gate).
- Client gained multipart support: `request` passes `FormData` through without
  a JSON content-type, exposed as `api.postForm` (reuses refresh-on-401).
- `api/data.ts` + `api/mailbox.ts`; `KbDocument`/`Mailbox` types;
  `KbStatusBadge`/`MailboxStatusBadge`; nav items added to `AppLayout`.
- Verified: lint, strict build, proxy auth-gating check on the new routes.

### Chunk 4 — draft review
- `TicketDetailPage` (`/tickets/:ticketId`): `GET /tickets/{id}` with
  loading/error states; ticket header (status + escalated badges), customer,
  and the full Message thread as bubbles (Customer vs Support; bodies rendered
  as **text**, never HTML). Queue cards now link here.
- `ReviewPanel` — the six review actions wired to `/messages/{id}/*`: editable
  draft textarea + Regenerate, Reject & escalate, Approve as-is, Save reply,
  and Send (enabled only once REVIEWED — the backend's two-step
  DRAFTED→REVIEWED→SENT flow). Per-action busy + error states; refetches on
  success, navigates to the queue on escalate.
- `api/messages.ts` (regenerate/save/approve/reject/send) + `api/tickets.getTicket`;
  `MessageDetail`/`TicketSummary`/`TicketDetailResponse` types (`QueueItem` now
  extends `MessageDetail`). `TicketStatusBadge`/`EscalatedBadge`; the
  `reviewStatusLabel` helper moved to `lib/labels.ts`.
- Verified: lint, strict build, and a live proxy check that
  `/tickets/{id}` + the message-action routes are reachable and auth-gated.

### Chunk 3 — review queue
- `AppLayout` — authed app shell (header with user/role + sign-out, nav,
  `Outlet`); protected routes now nest under it. The placeholder DashboardPage
  is gone; `/` is the review queue (the primary working surface).
- `ReviewQueuePage` — fetches `GET /tickets/queue` with explicit loading /
  empty / error states and a refresh button. Each row is a card: customer
  email, subject, the customer's message and the AI draft (rendered as **text**,
  never HTML — `whitespace-pre-wrap` + `line-clamp`), with intent + confidence
  badges. Backend returns these lowest-confidence-first.
- `ConfidenceBadge` (green ≥70 / amber ≥40 / rose <40) + `IntentBadge`
  (complaint highlighted). `api/tickets.getReviewQueue`; `QueueItem` type mirrors
  the enriched queue payload.
- Verified: lint, strict build, and a live proxy check that
  `/api/v1/tickets/queue` is reachable and auth-gated (403 without a token).

### Chunk 2 — auth
- Typed API client (`src/lib/client.ts`): bearer-auth requests, **transparent
  refresh-on-401** (single retry, deduped concurrent refreshes), and
  `ApiError` that normalises `{detail}` / 422 `[{loc,msg}]` envelopes into a
  human message. Token persistence in `src/lib/tokenStorage.ts` (localStorage —
  the backend returns the refresh token in JSON, not a cookie).
- Auth store: `AuthProvider` + `useAuth` (status `loading|authenticated|
  unauthenticated`, `login`/`logout`); validates a stored session via
  `GET /user/me` on load and drops to login on a hard refresh failure
  (`UNAUTHORIZED_EVENT`).
- Routing (react-router v6): `/login`, `/signup`, `/forgot-password`,
  `/reset-password`, and a `ProtectedRoute`-guarded `/` dashboard placeholder.
- Pages mirror backend validation (signup: 11 fields, email, password ≥ 8,
  password match; signup auto-logs-in since the endpoint returns ids not
  tokens). Reusable `TextField`/`Button`/`FormError`/`FormNotice` + `AuthCard`.
- Types in `src/lib/types.ts` mirror the backend schemas; auth calls in
  `src/api/auth.ts`. Verified: lint, build (strict `tsc`), and a live
  backend+proxy smoke test (`/health` and a `/api/v1/auth/login` 422 round-trip).

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
