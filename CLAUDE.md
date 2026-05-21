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
  encrypted mailbox credentials, pgvector).
- `SYSTEM_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_DOCUMENTATION.md` —
  the target system. Where code differs, these are the destination.
- `IMPLEMENTATION_ROADMAP.md` — the incremental, phase-by-phase plan.
- `.claude/agents/*.md` — specialist guidance per discipline.

Working principle: **harden incrementally, never big-bang.** Every change ships
behind the current working app.

## Running things

All commands must be run **from the repo root** — paths like `data/users/...`,
`email_queue.json`, and `saas.db` are resolved relative to the current working directory,
not the script location.

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

Build a company knowledge base (also done automatically by `POST /data/upload`):

```bash
python -m app.rag.preprocess --user_id <company_id>   # raw/ -> processed/documents.json
python scripts/build_rag.py   --user_id <company_id>   # processed/ -> FAISS index
```

There is **no test framework**. `scripts/test_query.py` and `scripts/test_email_listener.py`
are ad-hoc scripts you run directly with `python scripts/<name>.py`.

## Architecture: two layers

The codebase has two layers that the README's older "Project Structure" section does not
fully reflect:

- **`app/`** — the RAG/LLM/email engine. Pure, framework-agnostic modules (`rag/`,
  `llm/`, `email/`, `queue/`, `utils/`). Originally driven by standalone Streamlit apps
  (`chat_app.py`, `email_streamlit_ui.py`) and CLI `scripts/`.
- **`backend/`** — a FastAPI SaaS that *wraps* `app/`. It adds auth, a SQLite database,
  and per-company multi-tenancy. `backend/services/ai_service.py` is the bridge: it calls
  into `app.rag`, `app.llm`, and `app.email`.

`dashboard_app.py` is the current frontend and only talks to the FastAPI backend over
HTTP. The standalone Streamlit apps are the legacy single-tenant path.

### Request flow

```
Email created (POST /email/create  OR  email_worker.py fetching IMAP)
  -> row in emails table, status=NEW
  -> add_to_queue() appends to email_queue.json
  -> email_worker.py drains queue -> generate_email_reply()
       -> get_rag_context()  (FAISS retrieval)
       -> build_email_prompt() -> LLMClient.generate()  (Groq)
       -> confidence score
  -> status=AI_GENERATED, ai_reply + confidence saved
  -> dashboard GET /email/todo  (sorted ascending by confidence = lowest first)
  -> agent edits -> PUT /email/update-reply -> status=HUMAN_REVIEWED
  -> POST /email/send/{id} -> EmailSender SMTP -> status=SENT
```

The email `status` string (`NEW` -> `AI_GENERATED` -> `HUMAN_REVIEWED` -> `SENT`) is the
core state machine — most routes and dashboard logic branch on it.

### Multi-tenancy

- Auth: `POST /auth/signup` creates/links a `Company`; `POST /auth/login` returns a JWT
  carrying `user_id` + `company_id`. `get_current_user` (in `backend/auth/dependencies.py`)
  decodes it into a dict; routes scope every DB query by `user["company_id"]`.
- Knowledge bases live under `data/users/<company_id>/{raw,processed,vector_store}`,
  created by `WorkspaceManager`. `POST /data/upload` saves the file there and shells out
  (via `subprocess`) to `preprocess.py` then `build_rag.py` to retrain that company.

### Persistence

- **`saas.db`** — SQLite via SQLAlchemy. Models in `backend/models/`. Tables are
  auto-created on startup by `Base.metadata.create_all` in `backend/main.py`; there are
  no migrations, so schema changes mean editing the model and recreating the DB.
- **`email_queue.json`** — a flat JSON file used as the AI work queue between the API and
  `email_worker.py`. Not concurrency-safe.
- **FAISS index** — `data/users/<id>/vector_store/{faiss_index,docs.json}` per company.

## Stack

FastAPI + SQLAlchemy + SQLite backend; Streamlit frontend; Groq (`llama-3.3-70b-versatile`)
for generation; `sentence-transformers` BGE embeddings + `faiss-cpu` for retrieval; Gmail
IMAP/SMTP for email.

## Important gotchas

- **`app/rag/rag_pipeline.py` ignores `company_id`.** The vector path is hardcoded to
  `data/users/LabData/vector_store`, so every tenant currently retrieves from the same
  index. This breaks the multi-tenant promise — fix here if working on per-company RAG.
- **`backend/auth/jwt_handler.py` has a hardcoded `SECRET_KEY = "your_secret_key"`.**
  Move it to an env var before any real deployment.
- **Env var name drift.** `app/utils/config.py` reads `EMAIL_USER` / `EMAIL_PASS` and
  `GROQ_API_KEY`; the README mentions `EMAIL_PASSWORD`. Match `config.py`, not the README.
- The active model name lives in `app/llm/llm_client.py` (hardcoded), not in
  `Config.MODEL_NAME` (which is unused).
- `venv/` is committed to the repo; never edit or scan files under it.

## Project notes

- Code comments and variable notes mix English and Hindi/Urdu — this is expected.
- The README's structure diagram is partly stale (predates the `backend/` layer and
  `dashboard_app.py`); trust the code over the README for layout.
