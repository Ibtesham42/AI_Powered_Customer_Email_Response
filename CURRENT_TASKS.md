# Current Tasks

Active checkpoint: **Phase 3 chunk 3 COMPLETE** — the worker and the send
path are fully per-Company. On `feature/phase-3-mailbox`; Phases 0–2 are
merged to `main`. Next: Phase 3 chunk 4.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 3 Chunk 3 — done (worker polls each Company's mailbox)

- `scripts/email_worker.py` — `poll_mailboxes()` loops over every connected
  `Mailbox`, fetches via the connector, ingests into Tickets/Messages, and
  records `last_polled_at` / `status`. One mailbox failing never stops others.
- `routes/messages.py` send path replies from the Company's own mailbox
  (`mailbox_service.build_connector()`), not a global account.
- `INGEST_COMPANY_ID` and the global `EMAIL_USER`/`EMAIL_PASS` backend usage
  are gone.

See `CHANGELOG.md` for commit-level detail.

## ⚠️ Email now requires a connected mailbox

After chunk 3 the worker and the send route both need a per-Company `Mailbox`:
1. `MAILBOX_ENCRYPTION_KEY` must be set in `.env` (chunk 1).
2. Each Company must connect a mailbox via `POST /api/v1/mailbox/connect`
   (chunk 2) — otherwise ingestion is skipped and `send` returns `400`.

## Next: Phase 3 — Chunk 4 (DB-backed AI queue)

Retire `email_queue.json` (not concurrency-safe).

- The queue becomes a query: inbound `Message`s with
  `review_status = awaiting_ai`.
- The worker claims rows with `SELECT ... FOR UPDATE SKIP LOCKED` so multiple
  workers don't draft the same Message twice.
- Drop `app/email/email_queue.py` (and `app/queue/email_queue.py`),
  `add_to_queue` / `get_queue` / `clear_queue`, and the `email_queue.json` file.
- `email_worker.py` `process_queue()` reads from the DB instead.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-3-mailbox`; confirm `alembic current` =
   `0e9582994b57`.
3. Implement Chunk 4; commit; sync the docs.

## Remaining Phase 3 chunks
- Chunk 5 — forgot/reset password via the transactional email provider.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- IMAP/SMTP work needs live Gmail credentials — verify through the running
  app, not offline tests.
