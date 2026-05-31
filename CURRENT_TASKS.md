# Current Tasks

Active checkpoint: **Phase 6 chunk 2 done** (auth) on
`feature/phase-6-frontend`. Phases 0–5 are merged to `main`.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md` · ADR-0004 ·
History: `CHANGELOG.md`.

## ✅ Phase 6 Chunk 2 — done (auth)

- Typed API client with transparent refresh-on-401 + `ApiError` envelope
  parsing; localStorage token storage; auth store (`AuthProvider`/`useAuth`).
- react-router v6 routes: login/signup/forgot/reset + `ProtectedRoute` dashboard.
- Pages mirror backend validation; signup auto-logs-in. Reusable UI components.
- Verified: lint, strict build, and a live backend+proxy smoke test
  (`/health` + `/api/v1/auth/login` 422 round-trip). Real login/signup needs DB
  connectivity (Neon DNS was down in the sandbox) — contract/wiring proven.

## ✅ Phase 6 Chunk 1 — done (Vite + React scaffold)

- `frontend/`: Vite 5 + React 18 + TS (strict) + Tailwind v4 + ESLint + Prettier.
- Dev proxy `/api` + `/health` → backend `127.0.0.1:8000` (no CORS in dev).
- Landing page with a typed `/health` check (loading/ok/error). README written.
- Verified: `npm run lint`, `format:check`, `build` (with `tsc -b`) all clean.

## Phase 6 — Frontend (Vite + React) chunk plan
*ADR-0004. Built alongside Streamlit; cut over at parity. Roadmap has detail.*

0. ☑ Adopt Vite + React (ADR-0004; supersedes Streamlit-polish + Next.js).
1. ☑ Scaffold (Vite + TS + Tailwind, dev proxy, /health check).
2. ☑ Auth: typed API client, login/signup (mirror backend validation), auth
   store, protected routes, transparent token refresh on 401, forgot/reset.
3. ☐ Review queue (primary surface): `GET /tickets/queue`, confidence sort +
   escalation/intent badges; loading/empty/error states.
4. ☐ Draft review: approve/edit/rewrite/reject/regenerate/send + conversation
   history (Customer text rendered as text, never HTML).
5. ☐ KB upload panel (file/URL/FAQ) + mailbox connection panel.
6. ☐ Analytics / dashboard overview (`/dashboard`).
7. ☐ Cut over: serve the SPA + prod CORS; retire `dashboard_app.py`.

## Immediate next steps for the next session
1. Start Phase 6 chunk 3 — review queue (the primary working surface):
   `GET /api/v1/tickets/queue`, confidence sort, escalation/intent badges,
   loading/empty/error states. Add an app shell/layout + nav.

## Done so far
Phases 0–5 are on `main`: safety/cleanup, DB + auth, domain model
(Customer/Ticket/Message), mailbox + ingestion, RAG hardening (pgvector), and
the AI pipeline (structured generation, memory + summaries, escalation engine).
See `CHANGELOG.md` and `IMPLEMENTATION_ROADMAP.md` for the breakdown.

## Known cautions
- Backend has **no CORS** middleware yet — the SPA relies on Vite's dev proxy;
  production CORS/serving is a Phase 6 chunk 7 (cut-over) decision.
- Refresh token is returned in JSON today (not an httpOnly cookie); the auth
  chunk follows that until/unless the backend sets cookies.
- `TestClient` is broken — test via direct route-function calls (see
  `PROJECT_STATE.md` → Known bugs).
- The embedding model + Groq are heavy / need network — verify through the
  running app where practical.
