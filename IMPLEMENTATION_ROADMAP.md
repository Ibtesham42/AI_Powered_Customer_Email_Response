# Implementation Roadmap

Incremental refactor of the existing prototype into a production SaaS. Guiding
principle (from the design session): **harden incrementally, never big-bang.**
Every phase ends with a working app. No phase leaves the system broken.

Status legend: ☐ todo · ◐ in progress · ☑ done.

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
  Next.js frontend lands (Phase 7).
- ☑ Add `ruff` + `black` + `mypy` config (`pyproject.toml`,
  `requirements-dev.txt`); touched files are lint-clean. mypy is lenient —
  strictness ramps up per-module in later phases.
- ☑ Introduce structured logging (`backend/logging_config.py`); replaced
  `print` calls in the request path (routes, `llm_client`, `rag_pipeline`,
  `embeddings`).
- ☑ Add Alembic; baseline migration of the current schema
  (`alembic/versions/dd80321d216f_baseline_schema.py`); existing `saas.db`
  stamped at that revision.

## Phase 1 — Database & auth
*Goal: real DB, real tenancy, real sessions.*

- ☐ Add Postgres + pgvector to Docker Compose; switch `DATABASE_URL`.
- ☐ Retire `Base.metadata.create_all`; all schema via Alembic.
- ☐ Expand `Company` (address fields) and `User` (full_name, phone).
- ☐ **Fix the tenancy hole**: `signup` always creates a new Company; caller
  becomes `owner`. Remove join-by-name entirely.
- ☐ Validate signup input (Pydantic): email format, password strength,
  `password == verify_password`, phone/postal formats.
- ☐ Access token + refresh token: `refresh_tokens` table, `/refresh`,
  `/logout`, rotation, revocation.
- ☐ Rate limiting on `signup` / `login` / `forgot-password`.
- ☐ RBAC dependency: `require_owner`.
- ☐ `/api/v1` prefix on all routes.

## Phase 2 — Domain model: Customer + Ticket + Message
*Goal: replace the flat `emails` table with the real domain.*

- ☐ Create `customers`, `tickets`, `messages` models + migration.
- ☐ Implement the two state machines (ticket lifecycle, message review).
- ☐ Data migration: backfill from `emails` (see DATABASE_SCHEMA.md §migration).
- ☐ Repository layer: every query tenant-scoped by `company_id`.
- ☐ Rewrite Ticket/Message routes; drop the old `emails` table.
- ☐ `audit_logs` table + write security-relevant events.

## Phase 3 — Mailbox & ingestion
*Goal: per-Company email, safe credentials, safe queue.*

- ☐ `mailboxes` table; Fernet/KMS encryption helper for credentials.
- ☐ Mailbox connector abstraction (App Password impl now, OAuth-ready).
- ☐ `/mailbox/connect` — verify IMAP/SMTP before saving.
- ☐ Worker polls **each** Company's mailbox (remove hardcoded `company_id=1`
  and global `EMAIL_USER`).
- ☐ DB-backed queue: drop `email_queue.json`; queue = `messages WHERE
  review_status = awaiting_ai`, claimed with row locking.
- ☐ Customer/Ticket matching on inbound mail (thread → Ticket).
- ☐ Forgot/reset password via the transactional email provider.

## Phase 4 — RAG hardening
*Goal: real multi-tenant retrieval.*

- ☐ Move embeddings to pgvector (`kb_chunks`); per-Company isolation.
- ☐ **Fix `rag_pipeline.py`**: remove the hardcoded `LabData` path; scope by
  `company_id`.
- ☐ **Fix the reload bug**: load the embedding model once (process-level
  singleton), not per email.
- ☐ Replace `subprocess` KB training with an in-process background task.
- ☐ Multi-format ingestion: PDF, DOCX, CSV, TXT, URL, FAQ.
- ☐ Retrieval-grounded confidence (similarity + LLM self-rating).

## Phase 5 — AI pipeline
*Goal: structured, memory-aware, escalation-driven generation.*

- ☐ One structured Groq call → `{ intent, confidence, draft, needs_human }`.
- ☐ Move `GROQ` model name + params into config.
- ☐ Memory injection: current Ticket verbatim + past-Ticket summaries.
- ☐ Generate a Ticket `summary` on resolve/close.
- ☐ Hallucination-reduction prompt: answer only from context, otherwise
  defer to a human.
- ☐ Escalation engine: low confidence, human request, complaint, repeated
  replies, manual reject.

## Phase 6 — Dashboard polish (still Streamlit)
*Goal: full human-in-the-loop on the existing frontend.*

- ☐ Review queue with confidence sort + escalation badges.
- ☐ Approve / Edit / Rewrite / Reject / Regenerate actions.
- ☐ Ticket + Customer conversation-history view.
- ☐ KB upload panel with index status.
- ☐ Mailbox connection panel.
- ☐ Analytics page.

## Phase 7 — Next.js frontend
*Goal: the production UI; built alongside, cut over last.*

- ☐ Scaffold Next.js + TypeScript + Tailwind.
- ☐ Auth: login, signup, forgot/reset, protected routes, token refresh,
  session persistence.
- ☐ Dashboard, sidebar, review queue, KB panel, conversation history,
  settings, analytics.
- ☐ Cut over; retire Streamlit.

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
