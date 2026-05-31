# Implementation Roadmap

Incremental refactor of the existing prototype into a production SaaS. Guiding
principle (from the design session): **harden incrementally, never big-bang.**
Every phase ends with a working app. No phase leaves the system broken.

Status legend: ☐ todo · ◐ in progress · ☑ done.

**Current checkpoint:** Phases 0–5 merged to `main`. Phase 6 — the Vite + React
frontend (ADR-0004, supersedes the old Streamlit-polish + Next.js plans) — in
progress on `feature/phase-6-frontend`. See `CURRENT_TASKS.md` and
`PROJECT_STATE.md`.

---

## Phase 0 — Safety & cleanup  ☑ DONE
*Goal: remove footguns and dead code. No behaviour change.*

- ☑ Move `SECRET_KEY` and all secrets to environment variables; add
  `.env.example`. Fail fast on startup if a required var is missing.
  → `backend/config.py` (`Settings`, `_require`), `.env.example`.
- ☑ Delete `backend/routes/ai.py` (dead/broken) and drop its include.
- ☑ Fix `backend/main.py` duplicate imports and includes.
- ☑ Decide the fate of legacy standalone apps (`chat_app.py`,
  `email_streamlit_ui.py`) — **kept as reference** for now; remove once the
  Vite + React frontend lands (Phase 6; see ADR-0004).
- ☑ Add `ruff` + `black` + `mypy` config (`pyproject.toml`,
  `requirements-dev.txt`); touched files are lint-clean. mypy is lenient —
  strictness ramps up per-module in later phases.
- ☑ Introduce structured logging (`backend/logging_config.py`); replaced
  `print` calls in the request path (routes, `llm_client`, `rag_pipeline`,
  `embeddings`).
- ☑ Add Alembic; baseline migration of the current schema
  (`alembic/versions/dd80321d216f_baseline_schema.py`); existing `saas.db`
  stamped at that revision.

## Phase 1 — Database & auth  ☑ DONE
*Goal: real DB, real tenancy, real sessions.*

- ☑ Switch `DATABASE_URL` to Postgres — Neon managed cloud (pgvector
  available, enabled in Phase 4). Docker Compose for Postgres skipped in
  favour of managed cloud.
- ☑ Retire `Base.metadata.create_all` — schema is Alembic-only.
- ☑ Expand `Company` (address fields) and `User` (full_name, phone).
  → migration `3d3e063b9932`.
- ☑ **Fix the tenancy hole**: `signup` always creates a new Company; caller
  becomes `owner`. Join-by-name removed.
- ☑ Validate signup input (Pydantic): EmailStr, password ≥ 8,
  `password == verify_password`, no-blank fields.
- ☑ Access token + refresh token: `refresh_tokens` table, `/refresh`,
  `/logout`, rotation, revocation. → migration `fd095f9aa6c3`,
  `backend/services/auth_service.py`.
- ☑ Rate limiting (slowapi) on `signup` (5/min) and `login` (10/min).
  `forgot-password` rate limiting lands with that endpoint (Phase 3).
- ☑ RBAC dependency: `require_owner` — applied to `/data/upload`.
- ☑ `/api/v1` prefix on all feature routes (`/` and `/health` stay
  unversioned).

## Phase 2 — Domain model: Customer + Ticket + Message  ☑ DONE
*Goal: replace the flat `emails` table with the real domain.*

- ☑ Create `customers`, `tickets`, `messages` (+ `audit_logs`) models +
  migration `76870d572c26`. `backend/models/enums.py` holds the StrEnum
  value sets (ticket status, review status, direction, intent).
- ☑ Implement the two state machines — `backend/services/state_machine.py`
  (ticket lifecycle, message review) with transition validation.
- ☑ Data migration — N/A: the `emails` table is empty (0 rows), so there is
  no backfill. The table itself is dropped in chunk 3.
- ☑ Tenant-scoped service layer — `backend/services/ticket_service.py`;
  every query filtered by `company_id`.
- ☑ Rewrite Ticket/Message routes; drop the old `emails` table — chunk 3
  complete (sub-steps 3a–3f; migration `7d78ba51b1e8`).
- ☑ Write security-relevant events to `audit_logs` — chunk 4:
  `backend/services/audit_service.py`, events from the auth and message routes.

## Phase 3 — Mailbox & ingestion  ☑ DONE
*Goal: per-Company email, safe credentials, safe queue.*

- ☑ `mailboxes` table; Fernet encryption helper for credentials — chunk 1
  (`backend/crypto.py`, migration `0e9582994b57`).
- ☑ Mailbox connector abstraction (App Password impl now, OAuth-ready) —
  chunk 2 (`app/email/mailbox_connector.py`).
- ☑ `/mailbox/connect` — verify IMAP/SMTP before saving — chunk 2
  (`routes/mailbox.py`, `services/mailbox_service.py`).
- ☑ Worker polls **each** Company's mailbox; the send path also replies from
  the Company's own mailbox — chunk 3. `INGEST_COMPANY_ID` and the global
  `EMAIL_USER` are removed from the backend.
- ☑ DB-backed queue — chunk 4: `email_queue.json` dropped; the queue is
  `messages WHERE review_status = awaiting_ai`, claimed with
  `FOR UPDATE SKIP LOCKED`.
- ☑ Customer/Ticket matching on inbound mail (thread → Ticket) — done in
  Phase 2 (`find_or_open_ticket`, In-Reply-To threading); used by the worker.
- ☑ Forgot/reset password via the transactional email provider (Resend) —
  chunk 5 (`password_reset_tokens`, migration `3894e0ba0973`).

## Phase 4 — RAG hardening  ☑ DONE
*Goal: real multi-tenant retrieval.*

- ☑ Move embeddings to pgvector (`kb_chunks`); per-Company isolation —
  chunks 1–3 (extension + tables, write path, read path).
- ☑ **Fix `rag_pipeline.py`** — chunk 3: backend retrieval moved to
  `backend/services/rag_service.py` (pgvector, `company_id`-scoped); the
  FAISS `rag_pipeline.py` is now legacy-only (standalone apps).
- ☑ **Fix the reload bug** — `get_embedding_model()` process-level singleton;
  both the ingest and retrieval paths use it.
- ☑ Replace `subprocess` KB training with an in-process background task —
  chunk 2 (`/data/upload` → FastAPI `BackgroundTasks`).
- ☑ Multi-format ingestion: PDF, DOCX, CSV, TXT, JSON (chunk 2), URL, FAQ
  (chunk 4).
- ☑ Retrieval-grounded confidence — chunk 4: confidence from the top chunk's
  cosine similarity. (The LLM self-rating component is delivered by Phase 5's
  structured generation call.)

## Phase 5 — AI pipeline  ☑ DONE
*Goal: structured, memory-aware, escalation-driven generation.*

- ☑ One structured Groq call → `{ intent, confidence, needs_human, draft }` —
  chunk 2: `build_structured_prompt` + `LLMClient.generate_structured`
  (Groq JSON mode); `ai_service.generate_draft` parses/validates with a
  defer-to-human fallback; confidence blends retrieval similarity + self-rating.
- ☑ Move `GROQ` model name + params into config — chunk 1: `MODEL_NAME`,
  `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT` in `app/utils/config.py`;
  `LLMClient` reads them + `get_llm_client()` process singleton.
- ☑ Memory injection: current Ticket verbatim + past-Ticket summaries —
  chunk 3: `ai_service.build_memory` (past summaries budgeted to 1500 chars +
  current thread + current email).
- ☑ Generate a Ticket `summary` on resolve/close — chunk 3:
  `transition_ticket` calls `ai_service.summarize_ticket` on RESOLVED/CLOSED
  (best-effort, once). The `tickets.summary` column already existed.
- ☑ Hallucination-reduction prompt: answer only from context, otherwise
  defer to a human — chunk 2, folded into `build_structured_prompt` (grounding
  rules + the `needs_human` defer signal).
- ☑ Escalation engine: low confidence, human request, complaint, repeated
  replies, manual reject — chunk 4: `backend/services/escalation_service.py`
  (`evaluate` / `apply_draft_escalation`), wired into the worker and
  `/messages/{id}/regenerate`; thresholds in `backend/config.py`.

## Phase 6 — Frontend: Vite + React + TypeScript SPA  ◐ IN PROGRESS
*Goal: the production UI. Built alongside the working Streamlit dashboard; cut
over only at parity. Frontend holds no business logic — it renders state and
calls the `/api/v1` HTTP API. See ADR-0004.*

This phase supersedes the old "Phase 6 — Streamlit polish" and "Phase 7 —
Next.js" plans (collapsed into one; Streamlit `dashboard_app.py` is kept as the
working legacy UI until cut-over, then retired). Stack: Vite + React + TS
(strict) + Tailwind; typed API client mirroring the backend schemas; dev reaches
the backend via Vite's proxy (no CORS in dev).

- ◐ Chunk 1 — scaffold: Vite + React + TS + Tailwind in `frontend/`, ESLint +
  Prettier, dev proxy to `127.0.0.1:8000`, a minimal running app verifying the
  backend `/health`. README.
- ☐ Chunk 2 — auth: typed API client; login + signup (mirror backend
  validation); centralised auth store; protected routes; automatic transparent
  access-token refresh on 401; forgot/reset password.
- ☐ Chunk 3 — review queue: the primary surface. DRAFTED Messages
  (`GET /tickets/queue`), lowest confidence first, confidence + escalation +
  intent badges. Loading/empty/error states.
- ☐ Chunk 4 — draft review: Approve / Edit / Rewrite / Reject / Regenerate /
  Send; Ticket + Customer conversation-history view (Customer text rendered as
  text, never HTML).
- ☐ Chunk 5 — KB upload panel (file / URL / FAQ) with index status; mailbox
  connection panel.
- ☐ Chunk 6 — analytics / dashboard overview (`/dashboard`, ticket stats).
- ☐ Chunk 7 — cut over: serve the SPA + production CORS decision; retire
  `dashboard_app.py`.

## Cross-cutting (ongoing)

- ☐ Docker Compose: `api`, `worker`, `postgres`. Production: Cloud Run +
  Cloud SQL.
- ☐ Tests: introduce `pytest`; cover auth, tenancy isolation, the state
  machines, RAG scoping.
- ☐ CI: lint + type-check + tests on push.
- ☐ Monitoring: health/readiness probes, error tracking.

## Reference

- Glossary: `CONTEXT.md`
- Decisions: `docs/adr/0001`–`0003`
- Architecture: `SYSTEM_ARCHITECTURE.md`
- Schema: `DATABASE_SCHEMA.md`
- API: `API_DOCUMENTATION.md`
- Specialist guidance: `.claude/agents/*.md`
