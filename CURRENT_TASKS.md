# Current Tasks

Active checkpoint: **Phase 2, chunk 2 complete** on
`feature/phase-2-domain-model` (commit `0660ee0`, working tree clean).
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## Next: Phase 2 — Chunk 3 (the `emails` → Ticket/Message cutover)

The largest, highest-risk chunk. Sub-step it; keep the app working throughout.
The new models and services (`ticket_service`, `state_machine`) are built and
tested — this chunk wires them in and retires the legacy `emails` path.

1. **Ticket/Message routes** — replace `backend/routes/email.py` with
   ticket/message routes: list/get tickets, the review actions
   (approve / edit / reject / regenerate / send). Use `ticket_service` + the
   state machine. Tenant-scope via `get_current_user`'s `company_id`.
2. **AI service** — update `backend/services/ai_service.py` to read/write
   `Message` / `Ticket` instead of `Email`.
3. **Worker** — update `scripts/email_worker.py` ingestion:
   `get_or_create_customer` → find or `open_ticket` (by thread) → `add_message`.
4. **Dashboard route** — update `backend/routes/dashboard.py` stats to count
   tickets/messages.
5. **Streamlit** — update `dashboard_app.py`: its endpoints and field names
   change with the new routes.
6. **Data migration** — backfill `emails` rows → `customers` / `tickets` /
   `messages` (see `DATABASE_SCHEMA.md` → "Migration from the current schema").
7. **Drop `emails`** — final Alembic migration, once the backfill is verified.

## Immediate next steps for the next session

1. Read `PROJECT_STATE.md`, `CONTEXT.md`, `docs/adr/`.
2. `git checkout feature/phase-2-domain-model`; confirm
   `alembic current` = `76870d572c26`.
3. Begin Chunk 3 sub-step 1 (ticket/message routes) — additive where possible;
   keep the old `/api/v1/email/*` routes alive until the dashboard is switched,
   then remove them.
4. Commit per sub-step; update `IMPLEMENTATION_ROADMAP.md`, `CHANGELOG.md`,
   `API_DOCUMENTATION.md`, `DATABASE_SCHEMA.md` as each sub-step ships.

## After Phase 2 Chunk 3

- **Chunk 4** — write security-relevant events to `audit_logs`.
- Merge `feature/phase-2-domain-model` → `main` (on the user's explicit OK).
- **Phase 3** — mailbox connection (encrypted App Password), DB-backed queue
  (retire `email_queue.json`), forgot/reset password.

## Known blockers / cautions

- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- Chunk 3 touches many files; if a step breaks the app, stop and fix before
  proceeding — do not stack broken steps.
