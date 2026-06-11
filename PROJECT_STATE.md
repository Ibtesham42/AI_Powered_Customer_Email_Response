# Project State

Snapshot of the AI Customer Support SaaS as of **Phases 0–8 merged to `main`**
(2026-06-12). All Critical/High production-readiness blockers and the pilot
code blockers are closed; CI is green (tests + Docker build); the full workflow
is verified live (real Neon/Groq/Gmail) and the owner has run the user flow
locally end-to-end. Next step is the zero-budget pilot deployment (own PC +
Tailscale Funnel — `docs/runbooks/zero-budget-pilot.md`). The Vite + React SPA
is the primary UI (Streamlit retirement still pending formally). Phase plan:
`IMPLEMENTATION_ROADMAP.md` · Next work: `CURRENT_TASKS.md` ·
History: `CHANGELOG.md` · Glossary: `CONTEXT.md`.

## What this is

A multi-tenant SaaS: companies connect a support mailbox and a knowledge base;
a RAG + LLM pipeline drafts replies; staff review every reply before it sends.

## Architecture

Three layers (detail in `SYSTEM_ARCHITECTURE.md`):
- **`app/`** — framework-agnostic RAG / LLM / email engine.
- **`backend/`** — FastAPI SaaS: routes (under `/api/v1`), `auth/`,
  `services/`, `models/`, `config.py`, `logging_config.py`, `rate_limit.py`.
- **`dashboard_app.py`** — Streamlit admin dashboard (legacy; kept working
  until the React SPA reaches parity, then retired — ADR-0004).
- **`frontend/`** — the production UI: Vite + React + TS + Tailwind SPA
  (ADR-0004). Talks to the backend over `/api/v1` (Vite dev proxy). Has a typed
  API client with transparent refresh-on-401, an auth store, react-router
  routes (login/signup/forgot/reset), an `AppLayout` shell, the **review queue**
  at `/`, a **ticket detail / draft-review** view at `/tickets/:id`
  (regenerate/approve/edit/reject/send), a **knowledge base** panel
  (`/knowledge-base`: list + owner-only File/URL/FAQ upload) and a **mailbox**
  panel (`/mailbox`: details + owner-only connect), and an **overview**
  (`/overview`: ticket stats). The cut-over (serve SPA + prod CORS, retire
  Streamlit) is the remaining chunk.
- **`scripts/email_worker.py`** — background IMAP poll + AI queue worker.

## Completed modules

- **Auth** — signup (1 signup = 1 Company, signer = Owner), login, JWT access
  + refresh tokens (rotation/revocation), forgot/reset password (Resend
  email), `require_owner` RBAC, rate limiting.
- **Config / logging** — env-driven `backend/config.py` (fail-fast on missing
  secrets), structured `backend/logging_config.py`.
- **Domain model** — `Customer`, `Ticket`, `Message`, `AuditLog` models +
  `models/enums.py`; two state machines + tenant-scoped `ticket_service.py`.
- **Tickets/Messages API** — `/api/v1/tickets` (review queue, detail) and
  `/api/v1/messages` (regenerate / edit / approve / reject / send). The
  worker, AI service and Streamlit dashboard all run on this model; the
  legacy `emails` table, `Email` model and `/email` routes were removed.
- **Audit logging** — `audit_service.record()` writes an `AuditLog` row for
  `signup`, `login`, `login_failed`, `logout`, `message_sent` and
  `draft_rejected`. Audit-write failures are logged and swallowed.
- **Mailbox** — `mailboxes` table (one per Company); App Password stored
  Fernet-encrypted (`backend/crypto.py`). `MailboxConnector` abstraction
  (`app/email/mailbox_connector.py`, App Password impl) + `POST /mailbox/connect`
  (verifies IMAP **and** SMTP before saving) and `GET /mailbox`. The worker
  polls every connected mailbox; the send path replies from the Company's
  own mailbox. The backend no longer uses a global `EMAIL_USER`. **Key
  fail-fast (H3):** an invalid `MAILBOX_ENCRYPTION_KEY` aborts startup; a missing
  key aborts only when `MAILBOX_ENCRYPTION_REQUIRED=true`; without a usable key
  mailbox features refuse (connect → 503). Backup/recovery + rotation:
  `docs/runbooks/mailbox-encryption-key.md`.
- **AI draft queue** — no separate store: the worker drafts replies for
  inbound Messages with `review_status = awaiting_ai`, claimed with
  `FOR UPDATE SKIP LOCKED`. The `email_queue.json` file queue is retired.
- **LLM client** — Groq model name + params live in `app/utils/config.py`
  (`MODEL_NAME`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`),
  env-overridable; the Groq client carries a request timeout. Construct once
  per process via `app.llm.llm_client.get_llm_client()`.
- **Draft generation** — `ai_service.generate_draft` makes one structured Groq
  call (`build_structured_prompt` + `generate_structured`, JSON mode) returning
  `{intent, confidence, needs_human, draft}`. Malformed/empty output falls back
  to a safe defer-to-human result. Confidence blends retrieval similarity
  (primary) with the LLM self-rating (secondary). `intent` is persisted on the
  Message; `needs_human` is logged and awaits the chunk-4 escalation engine.
- **Memory + summaries** — `ai_service.build_memory` feeds the prompt this
  Customer's past-Ticket summaries (budgeted) + the current Ticket's thread +
  the current email. `transition_ticket` generates a 1-3 sentence
  `tickets.summary` on RESOLVED/CLOSED (best-effort; failure never breaks the
  transition), which becomes memory on the Customer's future Tickets.
- **Escalation engine** — `escalation_service` flags a Ticket as escalated when
  a fresh draft trips a rule (priority: `needs_human` → complaint → repeated
  replies → low confidence; manual reject is the fifth, at the reject route).
  Wired into the worker and the regenerate route. Thresholds
  (`ESCALATION_CONFIDENCE_THRESHOLD`, `ESCALATION_MAX_REPLIES`) are in
  `backend/config.py`. Escalated Tickets drop out of the auto-AI review queue.
- **Knowledge base** — `kb_documents` / `kb_chunks` on pgvector, per-Company.
  Ingestion is in-process (extract → chunk → embed → store) from file uploads
  (`/data/upload`), URLs (`/data/url`) and FAQ entries (`/data/faq`).
  `rag_service.retrieve` returns the nearest chunks by cosine distance,
  filtered by `company_id`; the top chunk's similarity grounds the AI draft
  confidence. The legacy FAISS path is standalone-apps-only.
- **Migrations** — Alembic; current head `a1b2c3d4e5f6` (adds
  `users.token_version`). Run `alembic upgrade head` on deploy.

## Deployment status

Not deployed. Local development only. Database is cloud (Neon). No Docker
(declined in favour of managed cloud Postgres). Eventual target: Cloud Run +
managed Postgres.

## Database state

- Engine: **Neon managed Postgres** — `DATABASE_URL` in `.env`.
- Tables: `companies`, `users`, `refresh_tokens`, `customers`, `tickets`,
  `messages`, `audit_logs`, `mailboxes`, `password_reset_tokens`,
  `kb_documents`, `kb_chunks`, `alembic_version`.
- pgvector: the `vector` extension is enabled; `kb_chunks.embedding` is
  `vector(768)` with an HNSW cosine index.
- Schema source of truth: Alembic (`alembic upgrade head`). No `create_all`.

## Auth state

- Access token: JWT, `ACCESS_TOKEN_EXPIRE_MINUTES` (default **30**). Carries a
  per-user `token_version`; `get_current_user` rejects a stale version (401).
  Revoke all access tokens via `POST /auth/logout-all` or a password reset
  (both bump `token_version` + revoke refresh tokens — `revoke_all_sessions`).
- Refresh token: opaque, SHA-256 hashed in `refresh_tokens`, 30-day default;
  rotated on `/auth/refresh`, revoked on `/auth/logout` (+ logout-all / reset).
- Password reset: `/auth/forgot-password` + `/auth/reset-password`; opaque
  SHA-256-hashed tokens in `password_reset_tokens`, single-use, 30-min
  default. Completing a reset revokes all the user's refresh tokens. Reset
  email sent via Resend (`email_service`).
- RBAC: roles `owner` / `agent`; `require_owner` dependency.
- Rate limiting: slowapi, in-memory store (needs Redis for multi-instance).

## Key architectural decisions

- ADR-0001 — Postgres, not Firestore.
- ADR-0002 — mailbox credentials = App Password, encrypted at rest.
- ADR-0003 — pgvector for embeddings.
- Neon cloud Postgres chosen over local Docker.
- Enum-ish columns stored as `String` + `StrEnum` app-layer validation (not
  native PG enums) — see `backend/models/enums.py`.
- Access token short (30 min) with `token_version`-based revocation (H2); the
  React SPA refreshes transparently, legacy Streamlit re-logs-in on expiry.
- Refresh token in an httpOnly+Secure+SameSite cookie scoped to `/api/v1/auth`
  (H1); `/refresh` + `/logout` read cookie-first with a body fallback for
  non-browser clients. SPA holds the access token in memory only and silently
  re-bootstraps from the cookie on load. Security headers + HSTS-in-prod;
  `ENVIRONMENT` / `COOKIE_*` config.

## Testing

- `pytest` suite in `tests/`: runs against in-memory SQLite, drives routes over
  `httpx.ASGITransport`. **81 tests** — state machine, escalation, AI
  confidence/parse, auth flow (incl. cookie transport), tenant isolation, token
  revocation, SSRF guard, mailbox key, monitoring, send idempotency, KB limits.
  Run: `pytest` (repo root; `pythonpath=["."]` in pyproject makes `backend`
  importable under bare pytest — same fix as `PYTHONPATH=/app` in the image).
- The SQLite schema excludes `kb_chunks` (pgvector) and `audit_logs` (JSONB);
  RAG-scoping + audit assertions need the Postgres-backed CI run (a commented
  job sketch exists in `.github/workflows/ci.yml`; tests not yet written).
- CI (`.github/workflows/ci.yml`, Phase 7 C2): GitHub Actions on push/PR runs
  `pytest` (blocking) + `ruff`/`black`/`mypy`/`pip-audit` (non-blocking).

## Deployment

- **Images/compose** (Phase 7 C2 + Phase 8): one shared non-root multi-stage
  `Dockerfile` runs `api`/`worker`/`migrate` (differ only by `command`);
  `docker-compose.yml` = local stack (pgvector pg16 + redis + one-shot migrate);
  `docker-compose.prod.yml` + `Caddyfile` = single-VPS stack (Caddy TLS only
  public service, DB on managed Postgres). CI builds the image on every push
  (`docker-build` job) with no-secret runtime smokes.
- Probes: `GET /health` (liveness, DB-free) and `GET /health/ready` (`SELECT 1`,
  503 if DB down). Worker: SIGTERM-graceful, crash backoff, heartbeat ping
  (`WORKER_HEARTBEAT_URL`); Sentry optional via `SENTRY_DSN` (fail-soft).
- Rate limiting uses Redis (`RATELIMIT_STORAGE_URI`); the app refuses to start
  in production without it. Env knobs: `DB_POOL_*`, `POLL_INTERVAL_SECONDS`
  (600 on Neon free tier so compute can autosuspend), `EMBEDDING_DEVICE`
  (**pin `cpu` on any single box running api+worker** — concurrent CUDA loads
  on a small GPU crash natively).
- **Active pilot plan ($0, no credit card)**: own PC + Tailscale Funnel +
  Upstash Redis + Neon free + Cloudflare Pages —
  `docs/runbooks/zero-budget-pilot.md`. Eliminated: Oracle (card), HF Spaces
  (**failed the mail-egress probe** — `deploy/hf-probe/` is reusable for any
  future host). Upgrade ladder: $10/yr domain → CF Tunnel; ~$9/mo → Hetzner
  via `docker-compose.prod.yml` (`docs/DEPLOYMENT_STRATEGY.md`).

## Active technical debt

- Alembic autogenerate flags redundant `ix_<table>_id` indexes on
  `audit_logs`, `customers`, `messages` and `tickets` — those models declare
  `index=True` on the PK column but the DB never got the index. Harmless
  noise; fix by dropping `index=True` from the PK columns.
- ~4 pre-existing ruff warnings in not-yet-touched files.
- `venv/` is committed to the repo (pre-existing).

## Known bugs / gotchas

- **`TestClient` (`fastapi.testclient`) is unusable** with httpx 0.28 (it drops
  the `app=` kwarg). Resolved for the suite by driving routes over
  `httpx.ASGITransport` (see `tests/conftest.py`); don't reach for `TestClient`.
- SQLAlchemy does **not** topologically order ORM deletes without
  `relationship()` declared — delete children before parents explicitly.
- `.env` holds secrets (`SECRET_KEY`, `DATABASE_URL`, API keys) — git-ignored;
  never commit or echo it.
