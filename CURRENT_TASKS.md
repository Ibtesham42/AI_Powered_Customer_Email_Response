# Current Tasks

Active checkpoint: **Phase 3 COMPLETE** (chunks 1–5) on
`feature/phase-3-mailbox`. Phases 0–2 are merged to `main`. Next: merge
Phase 3 to `main`, then Phase 4.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 3 Chunk 5 — done (forgot / reset password)

- `password_reset_tokens` table (migration `3894e0ba0973`, head) — single-use,
  short-lived; only the SHA-256 token hash is stored.
- `POST /api/v1/auth/forgot-password` — always `200` (no enumeration),
  rate-limited; emails a reset link via Resend.
- `POST /api/v1/auth/reset-password` — validates the token, sets the new
  password, consumes the token, revokes every refresh token.
- `password_reset_service`, `email_service` (Resend), and
  `auth_service.revoke_all_refresh_tokens`.

See `CHANGELOG.md` for commit-level detail.

## ⚠️ Verify the reset email against a real Resend account

The reset-email send cannot be unit-tested. Before relying on it:
1. Sign up at resend.com; put `RESEND_API_KEY` in `.env`. For a verified
   domain also set `RESEND_FROM_EMAIL` (the default `onboarding@resend.dev`
   only sends to your own Resend account email).
2. Run the app, `POST /api/v1/auth/forgot-password` with a registered email,
   confirm the email arrives, then `POST /api/v1/auth/reset-password` with the
   token from the link.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. Merge `feature/phase-3-mailbox` → `main` (on the user's OK).
3. Refresh `CLAUDE.md` if needed, then start Phase 4.

## Next: Phase 4 — RAG hardening
*Goal: real multi-tenant retrieval.*
- Move embeddings to pgvector (`kb_chunks`); per-Company isolation.
- **Fix `app/rag/rag_pipeline.py`** — it hardcodes the `LabData` vector path,
  so every tenant currently retrieves from the same index. Scope by
  `company_id`.
- Fix the reload bug: load the embedding model once (process-level singleton).
- Replace the `subprocess` KB training (`/data/upload`) with an in-process
  background task.
- Multi-format ingestion (PDF, DOCX, CSV, TXT, URL, FAQ).
- Retrieval-grounded confidence (similarity + LLM self-rating).

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- Live-credential paths (IMAP/SMTP, Groq/RAG, Resend) — verify through the
  running app, not offline tests.
