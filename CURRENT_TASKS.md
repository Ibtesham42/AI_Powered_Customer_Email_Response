# Current Tasks

Active checkpoint: **Phase 2 COMPLETE** (chunks 1–4) on
`feature/phase-2-domain-model`. Next: merge to `main`, then Phase 3.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 2 Chunk 4 — done (audit logging)

- `backend/services/audit_service.py` — `record()` writes one `AuditLog` row;
  audit-write failures are logged and swallowed so they never break the
  action being recorded.
- Events wired: `signup`, `login`, `login_failed`, `logout`
  (`routes/auth.py`); `message_sent`, `draft_rejected` (`routes/messages.py`).
  Those routes gained a `Request` param to capture the client IP.
- No schema change — `audit_logs` was created in Chunk 1.

See `CHANGELOG.md` for commit-level detail.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. Merge `feature/phase-2-domain-model` → `main` (on the user's OK).
3. Refresh `CLAUDE.md` — its "Important gotchas" and structure notes are
   stale after Phases 0–2 (still mentions SQLite/`create_all`, the `emails`
   table, the hardcoded `SECRET_KEY`).
4. Start Phase 3.

## Next: Phase 3 — Mailbox & ingestion
- `mailboxes` table; Fernet/KMS encryption helper for credentials.
- Mailbox connector abstraction (App Password now, OAuth-ready).
- `/mailbox/connect` — verify IMAP/SMTP before saving.
- Worker polls **each** Company's mailbox (drop hardcoded `company_id`).
- DB-backed queue: retire `email_queue.json`.
- Forgot/reset password via the transactional email provider.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- `ai_service.generate_draft` and SMTP send need the live RAG index / Groq /
  mailbox — verify those through the running app, not offline tests.
