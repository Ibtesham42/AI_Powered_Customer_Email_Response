# Database Architect

Owns the data model, migrations, multi-tenant isolation, and query performance.

## Responsibilities

- The Postgres schema (see `DATABASE_SCHEMA.md`) and its evolution.
- Alembic migrations — authoring, ordering, and safe rollout.
- pgvector setup for KB embeddings.
- Indexes, constraints, and the data migration off the legacy `emails` table.

## Coding standards

- Every schema change is an Alembic migration. `Base.metadata.create_all` is
  retired and must not return.
- Migrations are reviewed for reversibility and for locking behaviour on large
  tables.
- Native Postgres enum types for fixed value sets (see DATABASE_SCHEMA.md).
- `timestamptz` for all timestamps, never naive `timestamp`.

## Architecture rules

- **Every tenant-owned table has a non-null `company_id` FK.** No exceptions.
- Foreign keys are declared and enforced; no orphan rows.
- Uniqueness reflects the domain: `customers(company_id, email)`,
  `tickets(company_id, thread_id)` — a Customer is unique *within* a Company.
- `kb_chunks.embedding` is `vector(N)` where N matches the embedding model's
  dimension exactly; a mismatch is a hard failure.
- Relational data and vectors live in the **same** Postgres instance (ADR-0003).

## Best practices

- Index every FK used in a JOIN or filter, and every `company_id` column.
- The AI queue is a partial index: `messages(company_id) WHERE review_status
  = 'awaiting_ai'`.
- Vector retrieval filters `company_id` first, then orders by distance — build
  the HNSW/IVFFlat index accordingly.
- Data migrations are idempotent and verified with row counts before the old
  table is dropped.

## Security requirements

- Credentials and token values are stored as ciphertext or hashes only —
  `mailboxes.encrypted_credential`, `refresh_tokens.token_hash`,
  `password_reset_tokens.token_hash`. Never plaintext.
- Tenant isolation is a schema-level invariant; a missing `company_id` filter
  is a security bug, not a performance bug.
- Least-privilege DB roles in production; the app role cannot run DDL.

## Performance requirements

- Keep transactions short; do not hold one open across an LLM or network call.
- Use connection pooling sized to the deployment.
- Watch index bloat on `kb_chunks` as KBs grow; re-index when needed.
- Backups cover relational + vector data together (one logical backup).
