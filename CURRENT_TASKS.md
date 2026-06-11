# Current Tasks

Active checkpoint: **Phase 7 — production hardening, chunks 1–5 (C1, H4, H3, H2,
H1) done**; chunk 6 (C2) next. On `feature/phase-7-hardening`; Phases 0–6 merged
to `main`. Closing the Critical + High blockers from the production-readiness
audit. Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md` ·
History: `CHANGELOG.md`.

Test status: **63 tests green** (`pytest`). RAG-scoping + audit assertions
deferred to the Postgres CI run (chunk 6).
**Migration pending apply:** `a1b2c3d4e5f6` (users.token_version) — run
`alembic upgrade head` on deploy (couldn't run here; Neon DNS down).

## Phase 7 — production hardening (Critical + High audit blockers)
*Ordered by risk-reduction ÷ effort. Medium/Low audit items are out of scope.*

1. ☑ C1 — test harness + tenancy/auth/state-machine safety net (ASGITransport;
   pytest + pytest-asyncio; SQLite-backed auth/tenant tests; 35 green). **(High)**
2. ☑ H4 — SSRF guard on URL KB ingestion (`app/rag/url_guard.py`; validated at
   fetch + each redirect hop + the `/data/url` route; 16 tests). **(Low)**
3. ☑ H3 — mailbox encryption key: fail-fast at startup (invalid always; missing
   when `MAILBOX_ENCRYPTION_REQUIRED`), features refuse (503) without a key,
   backup/recovery + rotation runbook. 4 tests. **(Low)**
4. ☑ H2 — short access-token TTL (30 min) + revocation via per-user
   `token_version` claim; `POST /auth/logout-all`; reset bumps it. Migration
   `a1b2c3d4e5f6`. 4 tests. **(Medium)**
5. ☑ H1 — token transport hardening: refresh token → httpOnly+Secure+SameSite
   cookie scoped to `/api/v1/auth` (`backend/auth/cookies.py`; cookie-first,
   body fallback for non-browser clients); SPA access token in memory, silent
   cookie refresh on load; security-headers middleware + HSTS-in-prod; CORS
   credentials on. New `ENVIRONMENT`/`COOKIE_*` config. +4 tests. **(High)**
6. ☐ C2 — deployment & runtime: Docker + compose, worker auto-restart, Redis
   rate-limit, DB readiness probe, CI (lint+types+pytest w/ Postgres). **(High)**

Deferred (not in this plan): Phase 6 cut-over (retire Streamlit after a live
E2E test) and all audit Medium/Low items (idempotency, send retry, KB caps,
signup enumeration, audit gaps, pagination, etc.).

## Phase 6 — done (merged to `main`)
Vite + React SPA at feature parity: scaffold, auth (typed client + refresh-on-401),
review queue, ticket/draft review, KB + mailbox panels, overview, plus prod CORS +
`VITE_API_BASE_URL`. Only the cut-over (retire Streamlit after a live E2E test) is
deferred. Phases 0–5 (DB/auth, domain model, mailbox/ingestion, RAG, AI pipeline)
are also on `main`. Full breakdown: `CHANGELOG.md`.

## Known cautions
- `TestClient` is broken with httpx 0.28 (`app=` removed) — Phase 7 chunk 1
  switches tests to `httpx.ASGITransport`.
- pgvector `Vector` type is Postgres-only — SQLite test DB must exclude
  `kb_chunks`; RAG-scoping tests need a real pgvector DB (skip otherwise).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
- DB (Neon) host was unresolvable in the sandbox — live DB flows unverified here.
