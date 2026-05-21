# Changelog

Production-hardening refactor of the AI Customer Support SaaS. Newest first;
each entry references its git commit.

## Phase 2 — Domain model (in progress) · branch `feature/phase-2-domain-model`

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
