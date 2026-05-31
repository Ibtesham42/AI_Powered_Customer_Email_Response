# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A multi-tenant AI customer-support SaaS. Customer emails are answered by a RAG + LLM
pipeline, drafts go into a human-review queue, and an agent edits/approves before the
reply is sent over SMTP. Each company has an isolated knowledge base.

## Planning docs (read these before large changes)

The codebase is a working prototype being hardened into a production SaaS. The
*target* design and the reasoning behind it live in:

- `CONTEXT.md` — domain glossary. Use these exact terms (Company, User,
  Customer, Ticket, Message, Draft, Escalation).
- `docs/adr/` — recorded architecture decisions (Postgres-not-Firestore,
  encrypted mailbox credentials, pgvector, Vite+React frontend).
- `SYSTEM_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md` —
  the target system. Where code differs, these are the destination.
- `IMPLEMENTATION_ROADMAP.md` — the incremental, phase-by-phase plan.
- `.claude/agents/*.md` — specialist guidance per discipline.

Working principle: **harden incrementally, never big-bang.** Every change ships
behind the current working app.

## Running things

All commands must be run **from the repo root** — paths like `data/users/...`
are resolved relative to the current working directory, not the script location.

```bash
# Activate the env first
venv\Scripts\activate                         # Windows

# Apply database migrations (required on first run — schema is Alembic-managed)
alembic upgrade head

# FastAPI backend (the real entry point) — http://127.0.0.1:8000, docs at /docs
uvicorn backend.main:app --reload

# Streamlit admin dashboard — talks to the backend at 127.0.0.1:8000
streamlit run dashboard_app.py

# Background worker: polls Gmail IMAP + drains the AI queue every 10s
python scripts/email_worker.py
```

Knowledge bases are built by uploading files to `POST /api/v1/data/upload` — the
backend extracts, chunks, embeds and stores them in pgvector in-process. The
`app.rag.preprocess` / `scripts/build_rag.py` CLI scripts are the legacy FAISS
path, used only by the standalone Streamlit apps.

There is **no test framework**. `scripts/test_query.py` and `scripts/test_email_listener.py`
are ad-hoc scripts you run directly with `python scripts/<name>.py`.

## Architecture: two layers

The codebase has two layers that the README's older "Project Structure" section does not
fully reflect:

- **`app/`** — the RAG/LLM/email engine. Pure, framework-agnostic modules (`rag/`,
  `llm/`, `email/`, `queue/`, `utils/`). Originally driven by standalone Streamlit apps
  (`chat_app.py`, `email_streamlit_ui.py`) and CLI `scripts/`.
- **`backend/`** — a FastAPI SaaS that *wraps* `app/`. It adds auth, a Postgres
  database, the Customer/Ticket/Message domain model, and per-company
  multi-tenancy. `backend/services/ai_service.py` is the bridge: it calls
  into `app.rag`, `app.llm`, and `app.email`.

`dashboard_app.py` is the current frontend and only talks to the FastAPI backend over
HTTP. The standalone Streamlit apps are the legacy single-tenant path.

### Request flow

```
Inbound email (email_worker.py polling each Company's mailbox over IMAP)
  -> get_or_create_customer; find_or_open_ticket (In-Reply-To threading)
  -> inbound Message on the Ticket, review_status=AWAITING_AI
       (an awaiting_ai Message *is* the AI queue — no separate store)
  -> email_worker.py claims awaiting_ai Messages (FOR UPDATE SKIP LOCKED)
       -> ai_service.generate_draft()
       -> rag_service.retrieve()  (pgvector, company-scoped)
       -> build_structured_prompt() -> get_llm_client().generate_structured()
          (one Groq JSON call -> {intent, confidence, needs_human, draft})
       -> confidence = retrieval similarity blended with the LLM self-rating
  -> ticket_service.record_ai_draft(): ai_draft + confidence + intent saved,
     review_status=DRAFTED
  -> escalation_service.apply_draft_escalation(): escalate the Ticket on
     needs_human / complaint / repeated replies / low confidence
  -> dashboard GET /api/v1/tickets/queue  (lowest confidence first;
     escalated Tickets excluded)
  -> agent edits -> PUT /api/v1/messages/{id}/draft -> review_status=REVIEWED
  -> POST /api/v1/messages/{id}/send -> Company mailbox SMTP -> review_status=SENT,
     outbound Message created, Ticket -> PENDING
```

Two state machines drive the domain: the **Ticket** lifecycle
(`OPEN -> PENDING -> RESOLVED -> CLOSED`, plus an escalated flag) and the
per-**Message** review flow (`AWAITING_AI -> DRAFTED -> REVIEWED -> SENT`),
both validated in `backend/services/state_machine.py`.

### Multi-tenancy

- Auth: `POST /api/v1/auth/signup` always creates a *new* `Company` (the signer
  becomes its Owner — there is no join-by-name); `POST /api/v1/auth/login` returns
  a JWT carrying `user_id` + `company_id`, plus an opaque refresh token.
  `get_current_user` (in `backend/auth/dependencies.py`) decodes the JWT into a
  dict; routes scope every DB query by `user["company_id"]`.
- Knowledge bases: `POST /api/v1/data/upload` saves the file under
  `data/users/<company_id>/raw`, registers a `KbDocument`, and an in-process
  background task extracts/chunks/embeds it into the per-Company `kb_chunks`
  pgvector table. (Retrieval still reads the legacy FAISS index until Phase 4
  chunk 3.)

### Persistence

- **Postgres (Neon managed cloud)** — `DATABASE_URL` in `.env`; SQLAlchemy
  models in `backend/models/`. The schema is managed entirely by Alembic — run
  `alembic upgrade head`. `Base.metadata.create_all` is retired: a schema
  change means a new migration, never editing the model and recreating the DB.
- **AI draft queue** — not a separate store: inbound `Message`s with
  `review_status = awaiting_ai`. `email_worker.py` claims them with
  `SELECT ... FOR UPDATE SKIP LOCKED`.
- **Knowledge base** — per-Company embeddings in the `kb_chunks` pgvector table;
  retrieval is a `company_id`-filtered cosine-distance query.

## Stack

FastAPI + SQLAlchemy + Postgres (Neon) backend; Groq
(`llama-3.3-70b-versatile`) for generation; `sentence-transformers` BGE embeddings +
pgvector for retrieval; Gmail IMAP/SMTP for email. Frontend: Vite + React + TS +
Tailwind SPA in `frontend/` (ADR-0004), being built to replace the legacy
Streamlit `dashboard_app.py` (kept working until cut-over).

## Important gotchas

- **Two RAG paths.** The backend retrieves via `backend/services/rag_service.py`
  (pgvector, scoped by `company_id`). `app/rag/rag_pipeline.py` is the legacy FAISS
  path with a hardcoded shared index — standalone-app-only; never use it from the
  backend.
- **Env var name drift.** `app/utils/config.py` reads `EMAIL_USER` / `EMAIL_PASS` and
  `GROQ_API_KEY`; the README mentions `EMAIL_PASSWORD`. Match `config.py`, not the README.
- The Groq model name and generation params (`MODEL_NAME`, `LLM_TEMPERATURE`,
  `LLM_MAX_TOKENS`, `LLM_TIMEOUT`) live in `app/utils/config.py` (`Config`) and
  are env-overridable. `LLMClient` reads them; construct it once per process via
  `app.llm.llm_client.get_llm_client()` — never `LLMClient()` in the hot path.
- `venv/` is committed to the repo; never edit or scan files under it.

## Project notes

- Code comments and variable notes mix English and Hindi/Urdu — this is expected.
- The README's structure diagram is partly stale (predates the `backend/` layer and
  `dashboard_app.py`); trust the code over the README for layout.
