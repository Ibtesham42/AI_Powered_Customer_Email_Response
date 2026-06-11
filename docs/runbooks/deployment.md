# Runbook — Deployment & local container stack

How to run the stack in containers locally and how that maps to the production
target (Google Cloud Run + Cloud SQL). Scope: Phase 7 Chunk 6 (C2) — deployment
& runtime artefacts.

## The image

`api`, `worker`, and `migrate` all run from **one shared image**
(`./Dockerfile`, `python:3.12-slim`, non-root `appuser`). They differ only by
`command`. This is the Cloud Run pattern: one container image, multiple
deployments/jobs each with its own entrypoint.

Run commands (the contract every environment honours):

| Process | Command |
| ------- | ------- |
| api     | `uvicorn backend.main:app --host 0.0.0.0 --port 8000` |
| worker  | `python scripts/email_worker.py` |
| migrate | `alembic upgrade head` (one-shot) |

> The image is large (torch + sentence-transformers). Slimming it (CPU-only
> torch wheel, dropping legacy streamlit/faiss) is a deferred follow-up, not
> part of C2.

## Run locally with Docker Compose

```bash
# 1. Provide secrets/config — config is read from the environment, never baked
#    into the image. Compose loads it via env_file.
cp .env.example .env        # then fill in SECRET_KEY, GROQ_API_KEY, etc.

# 2. Bring the whole stack up.
docker compose up --build
```

Compose brings up, in order:

1. `db` (`pgvector/pgvector:pg16`) and `redis` (`redis:7-alpine`) — both gated by
   healthchecks.
2. `migrate` — runs `alembic upgrade head` once and exits (`restart: "no"`).
   Waits for `db: service_healthy`.
3. `api` and `worker` — both wait for
   `migrate: service_completed_successfully` **and** `db: service_healthy`, so
   the schema is always current before any app code runs. Migrations never run
   on app startup.

Compose overrides for the app services:

- `DATABASE_URL=postgresql://postgres:postgres@db:5432/acs`
- `RATELIMIT_STORAGE_URI=redis://redis:6379/0`
- worker only: `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=2` (single low-concurrency
  loop; the api uses pool defaults).

Postgres data persists in the named `pgdata` volume. `docker compose down`
keeps it; `docker compose down -v` wipes it.

## Health & readiness probes

| Endpoint            | Meaning   | Checks DB? | Use for |
| ------------------- | --------- | ---------- | ------- |
| `GET /health`       | liveness  | no (static `{"status":"ok"}`) | restart-if-dead probe |
| `GET /health/ready` | readiness | yes (`SELECT 1`, 503 if DB down) | gate traffic / startup |

- Compose's `api` healthcheck hits `/health` (liveness) via stdlib `urllib`.
- **Cloud Run**: map the *startup probe* to `/health/ready` (don't route traffic
  until the DB is reachable) and the *liveness probe* to `/health` (restart a
  wedged container without flapping on transient DB blips).

## Production env vars (Cloud Run)

Inject at runtime via Cloud Run env / Secret Manager — never in the image:

| Var | Notes |
| --- | ----- |
| `SECRET_KEY` | required at import time; from Secret Manager |
| `DATABASE_URL` | Cloud SQL connection (private IP / connector) |
| `MAILBOX_ENCRYPTION_KEY` | Fernet key; see mailbox-encryption-key runbook |
| `MAILBOX_ENCRYPTION_REQUIRED` | `true` in prod — api refuses to start without a valid key |
| `RATELIMIT_STORAGE_URI` | **required in prod** — the api refuses to start in production without it (an in-memory fallback would not hold across instances). **Treat as a secret**: managed Redis URIs embed a password (`rediss://:PASSWORD@host:6379/0`) — source it from Secret Manager and prefer TLS (`rediss://`). |
| `ENVIRONMENT` | `production` (enables Secure cookie + HSTS) |
| `COOKIE_SECURE` | `true` (API served over HTTPS) |
| `CORS_ORIGINS` | explicit SPA origin(s); no `*` with credentials |
| `GROQ_API_KEY` | required for AI replies |

worker deployment additionally sets `DB_POOL_SIZE=2` / `DB_MAX_OVERFLOW=2`.

## Migrations as a deploy step (Cloud Run analogue)

Locally the `migrate` service is the deploy-time migration. In production the
equivalent is a **pre-deploy migration run before routing traffic to the new
revision**:

1. Build & push the image (tagged by commit SHA).
2. Run `alembic upgrade head` once — as a **Cloud Run Job** (or a CI step) using
   a **DDL-capable database role**, against Cloud SQL. App runtime service
   accounts should be least-privilege and need not hold DDL rights.
3. Only after the migration job succeeds, deploy/route traffic to the new `api`
   and `worker` revisions.

This keeps schema changes out of app startup and makes deploys ordered and
rollback-able (migrations are forward-compatible; the previous revision keeps
serving until the new one is healthy).

## Hardening follow-ups (out of C2 scope)

Tracked for a later pass — flagged by the C2 security review, deliberately not
done here:

- **Pin base images by digest** (`python:3.12-slim@sha256:…`) for reproducible,
  tamper-evident builds; bump deliberately.
- **Container image CVE scanning** (Trivy/Grype on the built image) in CI — the
  ML stack (torch, sentence-transformers) has a non-trivial CVE surface.
  Dependency scanning (`pip-audit`) is already wired in (non-blocking).
- **Least-privilege runtime DB role** enforced in IaC (the runtime role should
  hold no DDL; only the migrate role does). Documented above but not yet
  exercised by an automated environment.
- **Image slimming** (CPU-only torch wheel, drop legacy streamlit/faiss path).
- **Lint/format CI baseline**: normalize the ~32 pre-existing non-conformant
  files (`black .` + `ruff --fix .`) and flip ruff/black from non-blocking to
  blocking in `.github/workflows/ci.yml`.
