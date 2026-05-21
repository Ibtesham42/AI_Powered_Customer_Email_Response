# Current Tasks

Active checkpoint: **Phase 2 chunk 3 COMPLETE** — the legacy `emails` flow is
fully retired. On `feature/phase-2-domain-model`. Next: Phase 2 chunk 4.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md`.

## ✅ Phase 2 Chunk 3 — done (sub-steps 3a–3f)

The Customer/Ticket/Message model fully replaced the legacy `emails` flow:
- **3a** Message-based AI generation · **3b** ticket/message routes ·
  **3c** worker ingest (In-Reply-To threading) · **3d** dashboard stats ·
  **3e** Streamlit re-point · **3f** deleted `routes/email.py`, the `Email`
  model, the legacy `ai_service` functions, and dropped the `emails` table.

See `CHANGELOG.md` for commit-level detail.

## Next: Phase 2 — Chunk 4 (audit logging)

Write security-relevant events to the `audit_logs` table (created in chunk 1).

- Add an `audit_service` that writes an `AuditLog` row: `action`,
  `company_id`, `user_id`, `entity_type` / `entity_id`, `ip_address`,
  `metadata`.
- Emit events from the relevant routes: `signup`, `login`, `logout`,
  message `send`, draft `reject` (escalation).
- Keep route handlers thin — an audit write is one service call.

## Immediate next steps for the next session
1. Read `PROJECT_STATE.md`.
2. `git checkout feature/phase-2-domain-model`; confirm `alembic current` =
   `7d78ba51b1e8`.
3. Implement Chunk 4 (audit logging); commit; sync the docs.
4. Then: merge `feature/phase-2-domain-model` → `main` (on the user's OK).
   A `CLAUDE.md` refresh is overdue — its "Important gotchas" and structure
   notes are stale after Phases 0–2.

## After Phase 2
- **Phase 3** — mailbox connection (encrypted App Password), DB-backed queue
  (retire `email_queue.json`), forgot/reset password.

## Known cautions
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- `ai_service.generate_draft` and SMTP send need the live RAG index / Groq /
  mailbox — verify those through the running app, not offline tests.
