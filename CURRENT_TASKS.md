# Current Tasks

Active checkpoint: **Phase 3 chunk 1 COMPLETE** — the `mailboxes` table and
credential encryption are in. On `feature/phase-3-mailbox`; Phases 0–2 are
merged to `main`. Next: Phase 3 chunk 2.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 3 Chunk 1 — done (mailboxes table + credential encryption)

- `mailboxes` table — one support mailbox per Company; migration
  `0e9582994b57` (head).
- `backend/crypto.py` — Fernet `encrypt`/`decrypt`. Key = `MAILBOX_ENCRYPTION_KEY`
  env var, read lazily (the app still starts without it; first use fails loudly).
- `backend/models/mailbox.py`; `MailboxProvider` / `MailboxStatus` enums.
- `cryptography` added to `requirements.txt`; `.env.example` updated.

See `CHANGELOG.md` for commit-level detail.

## ⚠️ Before the next session — set the encryption key

`MAILBOX_ENCRYPTION_KEY` is **not yet in `.env`**. Chunk 2 (`/mailbox/connect`)
needs it. Generate and add it:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Next: Phase 3 — Chunk 2 (mailbox connector + connect route)

- Mailbox connector abstraction — App Password impl now, OAuth-ready
  (all mailbox access goes through it; see ADR-0002).
- `POST /mailbox/connect` — verify IMAP **and** SMTP login before saving;
  store the App Password via `crypto.encrypt`; set `status`.
- Owner-only (`require_owner`); emit an audit event for the connect.
- Keep the route thin over a `mailbox_service`.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`; set `MAILBOX_ENCRYPTION_KEY` in `.env` (above).
2. `git checkout feature/phase-3-mailbox`; confirm `alembic current` =
   `0e9582994b57`.
3. Implement Chunk 2; commit; sync the docs.

## Remaining Phase 3 chunks
- Chunk 3 — worker polls **each** Company's mailbox (drop the hardcoded
  `INGEST_COMPANY_ID` / global `EMAIL_USER`).
- Chunk 4 — DB-backed queue: retire `email_queue.json`.
- Chunk 5 — forgot/reset password via the transactional email provider.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- IMAP/SMTP verification needs live Gmail credentials — verify chunk 2
  through the running app, not offline tests.
