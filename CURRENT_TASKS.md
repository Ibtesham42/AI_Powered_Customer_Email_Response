# Current Tasks

Active checkpoint: **Phase 3 chunk 2 COMPLETE** — the mailbox connector and
`/mailbox/connect` are in. On `feature/phase-3-mailbox`; Phases 0–2 are merged
to `main`. Next: Phase 3 chunk 3.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 3 Chunk 2 — done (mailbox connector + connect route)

- `app/email/mailbox_connector.py` — `MailboxConnector` abstraction;
  `AppPasswordConnector` (IMAP/SMTP). `verify()` checks both IMAP and SMTP
  login. `MailboxError` carries a user-facing message.
- `backend/services/mailbox_service.py` — `connect_mailbox()` verifies first,
  then stores the credential encrypted; a failed verify writes nothing.
- `POST /api/v1/mailbox/connect` (Owner-only, audited) + `GET /api/v1/mailbox`.
- `MailboxConnectRequest` schema; `mailbox_dict` serializer (no credential).

See `CHANGELOG.md` for commit-level detail.

## ⚠️ Verify chunk 2 against a real Gmail mailbox

The happy path needs live Gmail credentials and cannot be unit-tested. Before
relying on it:
1. Ensure `MAILBOX_ENCRYPTION_KEY` is set in `.env` (chunk 1 added it to
   `.env.example`; generate with
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
2. Run the app, log in as an Owner, `POST /api/v1/mailbox/connect` with a real
   Gmail address + App Password. Expect `200` and a `mailboxes` row;
   `GET /api/v1/mailbox` should show `status=connected`.

## Next: Phase 3 — Chunk 3 (worker polls each Company's mailbox)

- `scripts/email_worker.py` — replace the single global mailbox
  (`Config.EMAIL_USER` / `INGEST_COMPANY_ID`) with a loop over every Company
  that has a connected `Mailbox`.
- For each: decrypt the credential, build an `AppPasswordConnector`, fetch
  unread mail, ingest into Tickets/Messages (existing `ticket_service` flow).
- Update `mailbox.last_polled_at`; set `status=error` on a failed poll.
- The `connector.fetch_unread()` method already exists from chunk 2.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-3-mailbox`; confirm `alembic current` =
   `0e9582994b57`.
3. Implement Chunk 3; commit; sync the docs.

## Remaining Phase 3 chunks
- Chunk 4 — DB-backed queue: retire `email_queue.json`.
- Chunk 5 — forgot/reset password via the transactional email provider.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- IMAP/SMTP work needs live Gmail credentials — verify through the running
  app, not offline tests.
