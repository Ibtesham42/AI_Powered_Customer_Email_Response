# Current Tasks

Active checkpoint: **Phase 3 chunk 4 COMPLETE** — the JSON queue is retired.
On `feature/phase-3-mailbox`; Phases 0–2 are merged to `main`. Next: Phase 3
chunk 5 (the last Phase 3 chunk).
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 3 Chunk 4 — done (DB-backed AI queue)

- The AI queue is no longer a JSON file — it *is* inbound `Message`s with
  `review_status = awaiting_ai`.
- `email_worker.py` `process_queue()` claims Messages with
  `SELECT ... FOR UPDATE SKIP LOCKED`; the row lock releases only when
  `record_ai_draft` commits the move to `drafted`, so concurrent workers
  never draft the same Message twice. Failed drafts retry next cycle.
- Deleted `app/email/email_queue.py` and the `add_to_queue` call.
- Legacy `email_streamlit_ui.py` keeps its own `app/queue/email_queue.py`
  (untouched until Phase 7).

See `CHANGELOG.md` for commit-level detail.

## Next: Phase 3 — Chunk 5 (forgot/reset password)

The last Phase 3 chunk.

- `password_reset_tokens` table (already specced in `DATABASE_SCHEMA.md`):
  hashed token, short expiry, single-use (`used_at`).
- `POST /auth/forgot-password` — always returns `200` (no account
  enumeration); rate-limited; sends a reset link.
- `POST /auth/reset-password` — body: token + new password; validates,
  rotates the password, revokes the token, revokes refresh tokens.
- **Decide first:** how the reset email is sent. There is no longer a global
  backend mailbox; options are a transactional provider (SendGrid/Postmark/
  Resend — new dependency + API key) or sending via a Company mailbox. This
  needs a call before implementing — surface it to the user.
- Audit `password_reset_requested` / `password_reset_completed`.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-3-mailbox`; confirm `alembic current` =
   `0e9582994b57`.
3. Decide the reset-email transport (above), then implement Chunk 5.
4. After chunk 5: Phase 3 is complete — merge `feature/phase-3-mailbox`
   → `main` (on the user's OK).

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- IMAP/SMTP work and `ai_service.generate_draft` need live credentials /
  Groq / RAG — verify through the running app, not offline tests.
