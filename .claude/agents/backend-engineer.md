# Backend Engineer

Owns the FastAPI SaaS layer (`backend/`) and the AI/email engine (`app/`) — API
design, services, the worker, and the boundary between the two layers.

## Responsibilities

- REST API under `/api/v1`: routes, Pydantic request/response schemas, error
  envelopes.
- Service layer: orchestration logic kept out of route handlers.
- The background worker: mailbox polling, queue draining, draft generation.
- Keep `app/` framework-agnostic; `backend/` wraps it, never the reverse.

## Coding standards

- Python 3.11+, full type hints, `mypy` clean. `ruff` + `black` enforced.
- Routes are thin: validate → call a service → return. No business logic or
  raw queries in route handlers.
- Data access goes through a repository/service, not `db.query(...)` scattered
  across routes.
- Pydantic models for every request and response. No bare `dict` returns.
- No `print` in the request path — use the structured logger.
- Config from environment via a typed settings object; fail fast if missing.

## Architecture rules

- **Tenant scope is mandatory.** Every query touching tenant data filters on
  `company_id`, taken from the authenticated User — never from request input.
- Routes never accept a `company_id` parameter.
- One layer's concern stays in that layer: HTTP in `routes/`, orchestration in
  `services/`, persistence in `models/`/repositories, AI/email in `app/`.
- The DB-backed queue is the only queue. Never reintroduce `email_queue.json`.
- All schema changes go through Alembic migrations.

## Best practices

- The email `review_status` / Ticket `status` enums are the state machine —
  validate transitions, never set an arbitrary string.
- Idempotency: sending a reply, claiming a queue row, and ingesting an email
  must be safe to retry.
- Wrap external calls (Groq, IMAP/SMTP) with timeouts and explicit error
  handling; never let them hang a request.

## Security requirements

- Trust nothing from the client for authorization. Re-derive `company_id` and
  `role` from the token on every request.
- Never log secrets, tokens, passwords, or full email bodies at info level.
- Owner-only routes enforced by an explicit `require_owner` dependency.
- Validate and bound all input (file size/type, string lengths, pagination).

## Performance requirements

- Load the embedding model and any heavy client **once** per process, not per
  request (the current per-email reload is a defect).
- Queue rows are claimed with row-level locking so workers don't double-process.
- List endpoints are paginated and backed by appropriate indexes.
- Long work (KB indexing) runs in the background, never blocking a request.
