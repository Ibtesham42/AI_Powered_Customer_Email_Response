# Project State

Snapshot of the AI Customer Support SaaS as of **Phase 6 chunk 1**
(Phases 0–5 merged to `main`; the React frontend scaffold is on
`feature/phase-6-frontend`). Phase plan:
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
  panel (`/mailbox`: details + owner-only connect). Analytics + the cut-over
  are the remaining chunks.
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
  own mailbox. The backend no longer uses a global `EMAIL_USER`.
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
- **Migrations** — Alembic; current head `4da268d4e51a`.

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

- Access token: JWT, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480).
- Refresh token: opaque, SHA-256 hashed in `refresh_tokens`, 30-day default;
  rotated on `/auth/refresh`, revoked on `/auth/logout`.
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
- Access token kept long (480 min) so the legacy Streamlit dashboard works
  without silent refresh; lower it when the Next.js frontend ships.

## Active technical debt

- Alembic autogenerate flags redundant `ix_<table>_id` indexes on
  `audit_logs`, `customers`, `messages` and `tickets` — those models declare
  `index=True` on the PK column but the DB never got the index. Harmless
  noise; fix by dropping `index=True` from the PK columns.
- `TestClient` is broken (see Known bugs).
- ~4 pre-existing ruff warnings in not-yet-touched files.
- `venv/` is committed to the repo (pre-existing).

## Known bugs / gotchas

- **`TestClient` unusable** — httpx 0.28 dropped the `app=` kwarg this
  FastAPI/starlette version needs. Test via direct route-function calls with a
  hand-built `starlette.requests.Request`. Fix later: pin httpx `<0.28` or
  upgrade FastAPI/starlette.
- SQLAlchemy does **not** topologically order ORM deletes without
  `relationship()` declared — delete children before parents explicitly.
- `.env` holds secrets (`SECRET_KEY`, `DATABASE_URL`, API keys) — git-ignored;
  never commit or echo it.
