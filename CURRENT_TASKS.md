# Current Tasks

Active checkpoint: **Phase 6 chunk 5 done** (KB + mailbox panels) on
`feature/phase-6-frontend`. Phases 0–5 are merged to `main`.
Context: `PROJECT_STATE.md` · Plan: `IMPLEMENTATION_ROADMAP.md` · ADR-0004 ·
History: `CHANGELOG.md`.

## ✅ Phase 6 Chunk 5 — done (KB + mailbox panels)

- `KnowledgeBasePage` (`/knowledge-base`): document list + status badges +
  owner-only File/URL/FAQ uploader. Client gained `api.postForm` (multipart).
- `MailboxPage` (`/mailbox`): connected-mailbox details + owner-only connect
  form (404 = none). Agents get read-only + owner-only notices.
- `api/data.ts`, `api/mailbox.ts`, KB/Mailbox types + badges; nav items added.
- Verified: lint, strict build, proxy auth-gating on the new routes.

## ✅ Phase 6 Chunk 4 — done (draft review)

- `TicketDetailPage` (`/tickets/:ticketId`): `GET /tickets/{id}`, ticket header
  (status + escalated badges) + conversation thread (text, not HTML). Queue
  cards link here.
- `ReviewPanel`: the six actions on `/messages/{id}/*` — regenerate, reject &
  escalate, approve as-is, save reply, send (enabled only when REVIEWED).
  Per-action busy/error; refetch on success.
- `api/messages.ts` + `getTicket`; `MessageDetail`/`TicketDetailResponse` types.
- Verified: lint, strict build, proxy auth-gating check on the new routes.

## ✅ Phase 6 Chunk 3 — done (review queue)

- `AppLayout` app shell (header + nav + Outlet); `/` is now the review queue
  (DashboardPage placeholder removed).
- `ReviewQueuePage`: `GET /tickets/queue` with loading/empty/error + refresh;
  cards show customer/subject + message + AI draft (rendered as text) with
  intent + confidence badges (lowest confidence first). `ConfidenceBadge` /
  `IntentBadge`; `api/tickets.ts`; `QueueItem` type.
- Verified: lint, strict build, live proxy check (queue auth-gated, 403 w/o
  token). Queue data needs DB-backed login to view.

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
3. ☑ Review queue (primary surface): `GET /tickets/queue`, confidence sort +
   intent badges; loading/empty/error states. (Escalated Tickets are excluded
   from this queue by the backend — a separate escalations view is a later add.)
4. ☑ Draft review: approve/edit/rewrite/reject/regenerate/send + conversation
   history (Customer text rendered as text, never HTML).
5. ☑ KB upload panel (file/URL/FAQ) + mailbox connection panel.
6. ☐ Analytics / dashboard overview (`/dashboard`).
7. ☐ Cut over: serve the SPA + prod CORS; retire `dashboard_app.py`.

## Immediate next steps for the next session
1. Start Phase 6 chunk 6 — analytics / dashboard overview. Check the
   `/api/v1/dashboard` route (and `ticket_service.company_stats`) for the
   stats shape, then add an overview page with the counts.

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
