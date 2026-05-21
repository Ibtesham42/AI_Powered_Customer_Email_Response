# Current Tasks

Active checkpoint: **Phase 2 chunk 3 in progress — 3a, 3b, 3c, 3d done** on
`feature/phase-2-domain-model`. Context: `PROJECT_STATE.md` ·
Plan: `IMPLEMENTATION_ROADMAP.md`.

## In progress: Phase 2 — Chunk 3 (retire the `emails` flow)

Replaces the legacy `emails` table + `routes/email.py` + the emails-based
`ai_service` path with the Customer/Ticket/Message model. New code is
**additive**; the legacy path is removed only in the final sub-step, so the
app works throughout.

### Grilled decisions (do not re-litigate)
- **Coherent switch** — no parallel old/new routes; the Streamlit dashboard
  (the only API consumer) is updated in lockstep.
- **Worker tenancy** — the worker attaches ingested email to the Company named
  by a new `INGEST_COMPANY_ID` config var (per-company mailboxes are Phase 3).
- **Essentials-only routes** — build just what replaces `/email`; defer
  customers list / ticket assign / analytics.
- **Minimal dashboard re-point** — change endpoints + field names only; no UI
  redesign (Next.js replaces the dashboard in Phase 7).
- **No data backfill** — `emails` is empty (0 rows); just drop the table.

### Sub-steps
- ☑ **3a** — Message-based AI generation: `ai_service.generate_draft` +
  `get_ticket_history`; `ticket_service.record_ai_draft`. (`5f5eb9b`)
- ☑ **3b** — `routes/tickets.py` (review queue, list, detail) +
  `routes/messages.py` (regenerate / edit / approve / reject / send), thin
  over the services. `serializers.py` added; `InvalidTransitionError` → HTTP
  409 via an app exception handler.
- ☑ **3c** — `email_worker.py` ingests via `ticket_service`
  (`get_or_create_customer` → `find_or_open_ticket` with In-Reply-To
  threading → `add_message`), keyed by `INGEST_COMPANY_ID`. Worker
  converted to structured logging.
- ☑ **3d** — `routes/dashboard.py` `/stats` computes Ticket counts via
  `ticket_service.company_stats` (totals by status, escalated, review-queue
  depth).
- ☐ **3e** — `dashboard_app.py`: re-point to the new endpoints (minimal).
- ☐ **3f** — drop the legacy path: delete `models/email.py`,
  `routes/email.py`, the legacy `ai_service` functions; remove their imports
  from `main.py` + `alembic/env.py`; Alembic migration to DROP `emails`.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`; confirm branch `feature/phase-2-domain-model` and
   `alembic current` = `76870d572c26`.
2. Resume at **sub-step 3e** (re-point `dashboard_app.py`). Then 3f removes
   the legacy `/api/v1/email/*` routes and the `emails` table.
3. Commit per sub-step; sync `IMPLEMENTATION_ROADMAP.md`, `CHANGELOG.md`,
   `API_DOCUMENTATION.md`, `DATABASE_SCHEMA.md`.
4. Test via direct route-function calls (`TestClient` is broken — see
   `PROJECT_STATE.md`). `ai_service.generate_draft` needs the RAG index +
   Groq, so it is not unit-testable offline — verify it via the running app.

## After Chunk 3
- **Chunk 4** — write security-relevant events to `audit_logs`.
- Merge `feature/phase-2-domain-model` → `main` (on the user's explicit OK).
- **Phase 3** — mailbox connection, DB-backed queue, password reset.

## Cautions
- Chunk 3 touches many files — if a sub-step breaks the app, fix it before
  proceeding; do not stack broken steps.
- New code stays additive; the `emails` path remains runnable until 3f.
