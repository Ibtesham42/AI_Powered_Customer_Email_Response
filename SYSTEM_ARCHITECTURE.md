# System Architecture

The target architecture for the AI Customer Support SaaS. This reflects the
decisions made in the design session — see `CONTEXT.md` for the glossary and
`docs/adr/` for the recorded trade-offs. Where the current code differs, this
document describes the destination, and `IMPLEMENTATION_ROADMAP.md` describes
how to get there incrementally.

## 1. Overview

A multi-tenant SaaS. Each **Company** connects its support mailbox and uploads
a **Knowledge base**. Inbound **Customer** email is turned into **Tickets**;
a RAG + LLM pipeline drafts replies; a **User** (Owner or Agent) reviews and
sends every reply. In v1 no reply is sent without human approval.

## 2. Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend                                                     │
│  - Streamlit dashboard  (current, stays live during rebuild)  │
│  - Next.js + TypeScript + Tailwind  (target, built alongside) │
└───────────────┬───────────────────────────────────────────────┘
                │  HTTPS  /api/v1
┌───────────────▼───────────────────────────────────────────────┐
│  backend/  — FastAPI SaaS layer                                │
│  - routes/      versioned REST API                             │
│  - auth/        JWT access + refresh, RBAC, hashing            │
│  - services/    orchestration (ai_service, mailbox, kb)        │
│  - models/      SQLAlchemy ORM                                 │
│  - repositories/  data access, tenant-scoped queries           │
└───────────────┬───────────────────────────────────┬───────────┘
                │                                   │
┌───────────────▼─────────────┐   ┌─────────────────▼───────────┐
│  app/  — AI/email engine     │   │  worker  — background loop  │
│  - rag/    chunk, embed,     │   │  - poll Company mailboxes   │
│            retrieve (pgvector)│  │    (IMAP)                   │
│  - llm/    Groq client,      │   │  - drain DB-backed queue    │
│            prompt building   │   │  - generate drafts          │
│  - email/  IMAP/SMTP         │   │  - summarise closed Tickets │
│            connectors        │   └─────────────────────────────┘
└───────────────┬─────────────┘
                │
┌───────────────▼───────────────────────────────────────────────┐
│  Persistence                                                   │
│  - Postgres  (Cloud SQL in prod)  — relational data            │
│  - pgvector  (extension)          — KB embeddings              │
│  - object storage / disk          — raw uploaded KB files      │
└───────────────────────────────────────────────────────────────┘
```

`app/` stays framework-agnostic (no FastAPI imports). `backend/` wraps it.
The worker is a separate process sharing `app/` and `backend/models`.

## 3. Core domain

See `CONTEXT.md` for definitions. The entity graph:

```
Company 1───* User
Company 1───1 Mailbox
Company 1───* Customer
Company 1───* KBDocument 1───* KBChunk(embedding)
Customer 1───* Ticket 1───* Message
```

Every table carries `company_id`. Every query is scoped by it — tenant
isolation is a `WHERE company_id = ?` filter, never optional.

## 4. Request flows

### 4.1 Inbound email → sent reply

```
Worker polls Company mailbox (IMAP)
  → match/create Customer by (company_id, from-address)
  → match Ticket by email thread, else open a new Ticket
  → insert inbound Message (review_status = AWAITING_AI)
  → [DB queue: rows WHERE review_status = AWAITING_AI]
Worker drains queue
  → build Memory (current Ticket + past-Ticket summaries)
  → RAG retrieve from pgvector (scoped to company_id)
  → one structured Groq call → { intent, confidence, draft }
  → store draft, intent, confidence; review_status = DRAFTED
  → apply escalation rules (low confidence / human-request /
    complaint / repeated replies) → Ticket.escalated
Dashboard shows the review queue (sorted ascending by confidence)
  → User Approves / Edits / Rewrites → review_status = REVIEWED
    or Rejects → Ticket escalated
  → User sends → SMTP via Company mailbox → outbound Message,
    review_status = SENT
```

### 4.2 Signup

```
POST /api/v1/auth/signup
  → ALWAYS create a new Company (never join by name)
  → create User as Owner of that Company
  → issue access + refresh tokens
```

### 4.3 Knowledge base upload

```
POST /api/v1/kb/documents  (file)
  → store raw file, KBDocument(status = UPLOADED)
  → background task: extract text → chunk → embed →
    insert KBChunks with embeddings into pgvector
  → KBDocument(status = INDEXED)
```

## 5. Cross-cutting concerns

- **Auth**: short-lived access JWT + revocable refresh token (DB row).
  RBAC: Owner (company settings, mailbox, billing) vs Agent (review queue).
- **Secrets**: all from environment. No secret in source. Mailbox App
  Passwords encrypted at rest with a Fernet/KMS key (ADR-0002).
- **API versioning**: every route under `/api/v1`.
- **Rate limiting**: on auth endpoints (signup, login, reset).
- **Migrations**: Alembic. `Base.metadata.create_all` is retired.
- **Logging**: structured JSON logs; every request carries a correlation id.
- **Audit log**: security-relevant actions written to `audit_logs`.
- **Error handling**: typed exceptions → consistent JSON error envelope.

## 6. Deployment

Local: Docker Compose — `api`, `worker`, `postgres` (with pgvector).
Production target: Google Cloud — Cloud SQL (Postgres) + Cloud Run (`api`)
+ Cloud Run job or always-on instance (`worker`). Frontend on Vercel or
Cloud Run.

## 7. Known gaps deliberately deferred to v2

- Gmail OAuth (replacing App Passwords) — ADR-0002.
- Multi-user companies via email invites.
- Configurable per-Company auto-send above a confidence threshold.
- Vector-retrieval of relevant past Messages for Memory.
- Gmail push notifications (requires OAuth) instead of IMAP polling.
