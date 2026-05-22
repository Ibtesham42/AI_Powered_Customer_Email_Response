# Project State

Snapshot of the AI Customer Support SaaS as of **Phase 2 complete**
(chunks 1–4). Phase plan: `IMPLEMENTATION_ROADMAP.md` · Next work:
`CURRENT_TASKS.md` · History: `CHANGELOG.md` · Glossary: `CONTEXT.md`.

## What this is

A multi-tenant SaaS: companies connect a support mailbox and a knowledge base;
a RAG + LLM pipeline drafts replies; staff review every reply before it sends.

## Architecture

Three layers (detail in `SYSTEM_ARCHITECTURE.md`):
- **`app/`** — framework-agnostic RAG / LLM / email engine.
- **`backend/`** — FastAPI SaaS: routes (under `/api/v1`), `auth/`,
  `services/`, `models/`, `config.py`, `logging_config.py`, `rate_limit.py`.
- **`dashboard_app.py`** — Streamlit admin dashboard (legacy; Next.js planned).
- **`scripts/email_worker.py`** — background IMAP poll + AI queue worker.

## Completed modules

- **Auth** — signup (1 signup = 1 Company, signer = Owner), login, JWT access
  + refresh tokens (rotation/revocation), `require_owner` RBAC, rate limiting.
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
- **Migrations** — Alembic; current head `7d78ba51b1e8`.

## Deployment status

Not deployed. Local development only. Database is cloud (Neon). No Docker
(declined in favour of managed cloud Postgres). Eventual target: Cloud Run +
managed Postgres.

## Database state

- Engine: **Neon managed Postgres** — `DATABASE_URL` in `.env`.
- Tables: `companies`, `users`, `refresh_tokens`, `customers`, `tickets`,
  `messages`, `audit_logs`, `alembic_version`. (The legacy `emails` table
  was dropped in Chunk 3.)
- pgvector: extension available on the instance; enabled in Phase 4.
- Schema source of truth: Alembic (`alembic upgrade head`). No `create_all`.

## Auth state

- Access token: JWT, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480).
- Refresh token: opaque, SHA-256 hashed in `refresh_tokens`, 30-day default;
  rotated on `/auth/refresh`, revoked on `/auth/logout`.
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

- `email_queue.json` JSON queue still in use — replaced by a DB-backed queue
  in Phase 3. (The legacy `emails` table/model/routes are gone.)
- `CLAUDE.md` "Important gotchas" / structure notes are partly stale after
  Phases 0–2 — a CLAUDE.md refresh is overdue.
- `app/rag/rag_pipeline.py` hardcodes the `LabData` vector path — Phase 4.
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
