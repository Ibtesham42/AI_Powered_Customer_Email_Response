# Current Tasks

Active checkpoint: **Phases 0–8 merged to `main`; CI fully green (lint-test +
docker-build); local production smoke test 16/16; the owner has run the full
user flow locally** (real Gmail inbound → tickets → drafts → review UI). The
pilot deployment plan is **own PC + Tailscale Funnel** ($0, no credit card —
Oracle and Hugging Face were eliminated; HF failed the mail-egress probe). See
`docs/runbooks/zero-budget-pilot.md`.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md` ·
History: `CHANGELOG.md`.

Test status: **81 tests green** (`pytest`). RAG-scoping + audit assertions still
deferred (SQLite-only suite; commented Postgres+pgvector CI job sketch ready).

## Next: pilot launch (infra/accounts, not code)
1. ☐ Tailscale + Upstash accounts (SSO, no card) → `tailscale funnel 8000`.
2. ☐ `.env.pilot` per runbook §2 (fresh secrets; `EMBEDDING_DEVICE=cpu` and
   `POLL_INTERVAL_SECONDS=600` are mandatory on this box).
3. ☐ Cloudflare Pages deploy of `frontend/` (`VITE_API_BASE_URL`,
   `COOKIE_SAMESITE=none`).
4. ☐ Monitoring accounts (Sentry / Healthchecks.io / UptimeRobot) → env vars.
5. ☐ Verify checklist incl. send-from-queue on the dedicated mailbox; B-4
   inbound path already proven in the local run.
6. ☐ Invite the pilot company (checklist in `docs/LAUNCH_READINESS.md`).
## Done (full history in `CHANGELOG.md`)
- **Phases 0–6**: DB/auth → domain model → mailbox/ingestion → RAG (pgvector)
  → AI pipeline → Vite/React SPA at feature parity.
- **Phase 7** (production hardening): test harness, SSRF guard, mailbox-key
  fail-fast, token TTL+revocation, cookie token transport, Docker/compose/CI.
- **Phase 8** (pilot readiness): Sentry + worker heartbeat, send idempotency
  (atomic SENDING claim), KB upload limits, `docker-compose.prod.yml` + Caddy.
- **Post-Phase-8 fixes**: `POLL_INTERVAL_SECONDS` + `EMBEDDING_DEVICE` env
  knobs, pytest/CI package-discovery fix, test-dep pins, escalated-tickets
  section in the Review Queue UI, `.gitattributes` LF for shell scripts.
- Live verifications: 11-step e2e (real Neon/Groq/Gmail), 16/16 production
  smoke test, owner-run local user flow (real inbound mail → drafts → UI).

Deferred: Streamlit cut-over; C2 hardening follow-ups (digest-pinned images,
image CVE scan, image slimming, flip ruff/black to blocking); audit Medium/Low
leftovers (signup enumeration, audit gaps, pagination).

## Known cautions
- `TestClient` is broken with httpx 0.28 — tests use `httpx.ASGITransport`;
  test-critical deps are pinned (`httpx==0.28.1`, `pytest==9.0.3`).
- pgvector `Vector` is Postgres-only — SQLite test DB excludes `kb_chunks` +
  `audit_logs`; RAG-scoping tests need a real pgvector DB.
- `backend`/`app` are NOT pip-installed — `pythonpath=["."]` (pyproject) and
  `PYTHONPATH=/app` (Docker) make them importable; don't remove either.
- **Single-box GPU**: api + worker both load the BGE model; concurrent CUDA
  loads on a small GPU crash natively → pin `EMBEDDING_DEVICE=cpu`.
- **The worker marks fetched mail read** and ingests *all* unread mail —
  never connect a personal/shared inbox; zero the inbox before connecting.
- Local dev DB is shared with the owner's test company ('sham', real mailbox
  connected) — don't bulk-delete Neon rows without asking.
