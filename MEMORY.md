# Project Memory

Orientation for anyone — human or agent — picking up this repository. Read the
linked docs before changing code.

## Read first
- `CLAUDE.md` — project overview and commands
- `PROJECT_STATE.md` — current state snapshot
- `CURRENT_TASKS.md` — what to do next
- `IMPLEMENTATION_ROADMAP.md` — the phased plan
- `CONTEXT.md` — domain glossary (use these exact terms)
- `docs/adr/` — recorded architecture decisions
- `CHANGELOG.md` — what has shipped

## Invariants — do not break
- **Tenant isolation**: every query on tenant data filters by `company_id`,
  taken from the authenticated token — never from request input.
- **Incremental, never big-bang**: every change ships behind a working app;
  commit per chunk/sub-step.
- **Schema via Alembic only**: no `Base.metadata.create_all`; use
  `alembic upgrade head`.
- **Secrets live in `.env`** (git-ignored): never commit or echo it.
- **Docs tracked per chunk**: update the roadmap, `API_DOCUMENTATION.md` and
  `DATABASE_SCHEMA.md` as work ships.

## Current checkpoint
Phase 2 chunk 2 done · branch `feature/phase-2-domain-model` · commit
`0660ee0`. Next: Phase 2 chunk 3 — the `emails` → Ticket/Message cutover.

## Project facts
- Database: **Neon managed Postgres** (cloud); `DATABASE_URL` in `.env`.
- Stack: FastAPI + SQLAlchemy + Alembic; Streamlit dashboard; Groq LLM;
  pgvector (Phase 4).
- `main` carries Phase 0 + Phase 1; Phase 2 is on its feature branch.
