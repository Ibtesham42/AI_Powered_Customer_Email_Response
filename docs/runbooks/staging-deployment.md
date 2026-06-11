# Staging Deployment Plan

_Plan only — not yet implemented. Target stack: Google Cloud Run (api + worker)
+ Neon Postgres/pgvector + managed Redis + a static-hosted Vite/React SPA.
Staging mirrors production at smaller scale so the deploy path, migrations,
cookie/CORS behaviour, and monitoring are all proven before any company touches
prod. Companion docs: `docs/runbooks/deployment.md`, `docs/LAUNCH_READINESS.md`._

## 0. Prerequisites / gates before standing up staging

- [x] Image builds on Linux (CI `docker-build` green — blocker B-1 closed).
- [ ] CI fully green (lint-test pytest fix verifying).
- [ ] A **dedicated** staging support mailbox (Gmail App Password) — never a
      personal inbox; the worker marks fetched mail read.
- [ ] Staging secrets minted (separate from prod): `SECRET_KEY`,
      `MAILBOX_ENCRYPTION_KEY`, DB URL, Redis URL, `GROQ_API_KEY`, `RESEND_API_KEY`.
- [ ] DNS names chosen: `api.staging.<domain>` and `app.staging.<domain>`.

Decisions to lock first (drive cookie/CORS config):
- **Origin topology.** Recommended: serve SPA and API on the **same parent
  domain** (e.g. SPA `app.staging`, API `api.staging`) and use
  `COOKIE_SAMESITE=lax` only if truly same-site; otherwise treat as separate
  origins → `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true` + explicit
  `CORS_ORIGINS`. Simplest robust option: **reverse-proxy the API under the SPA
  origin** (`/api/*`) so cookies are first-party (`SameSite=lax`, no CORS).
- **Environment flag.** Set `ENVIRONMENT=production` on staging too (it is served
  over HTTPS), so Secure cookies + HSTS + the Redis rate-limit fail-fast all
  match prod. (The code only special-cases `production`; a separate "staging"
  value would silently disable those.)

---

## 1. Frontend deployment (Vite + React SPA)

- **Build**: `cd frontend && npm ci && npm run build` → static `dist/`.
  Inject `VITE_API_BASE_URL` at build time:
  - same-origin (reverse-proxy): leave unset/relative.
  - separate-origin: `VITE_API_BASE_URL=https://api.staging.<domain>`.
- **Host**: static hosting + CDN — Firebase Hosting, Cloud Storage + Cloud CDN,
  or Cloud Run (nginx serving `dist/`). Serve over HTTPS with the SPA fallback
  (all routes → `index.html`).
- **Security headers** at the static host: `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, a CSP for the SPA, and HSTS.
- **Cut-over note**: the SPA is the intended UI; the legacy Streamlit dashboard
  is **not** deployed to staging. Confirm the SPA covers every needed flow first.
- **Verify**: load the app, complete login (confirm the refresh cookie is set
  `HttpOnly; Secure; SameSite=…` and the access token lives only in memory),
  exercise queue → draft → send against the staging API.

## 2. Backend deployment (api + worker, one image)

- **Image**: the existing shared `Dockerfile`, tagged by commit SHA
  (`api:staging-<sha>`); pushed to Artifact Registry. (Built/validated by CI.)
- **`api` service** (Cloud Run): command
  `uvicorn backend.main:app --host 0.0.0.0 --port 8000`; min-instances 0–1,
  modest CPU/RAM (the embedding model is loaded by the **worker**, not the api).
  Startup probe → `/health/ready`; liveness probe → `/health`. HTTPS via the
  Cloud Run domain mapping.
- **`worker` service** (Cloud Run, always-on): command
  `python scripts/email_worker.py`; **min-instances ≥ 1** (it polls + drains
  continuously and self-heals on crash / shuts down cleanly on SIGTERM). Heavier
  RAM (loads the BGE embedding model). Smaller DB pool: `DB_POOL_SIZE=2`,
  `DB_MAX_OVERFLOW=2`. No public ingress.
  - **First-run model fetch**: the worker downloads BGE weights from HuggingFace
    on first embed — ensure egress is allowed (or bake/mount a model cache).
- **migrate** (pre-deploy, see §3): a Cloud Run **Job** running
  `alembic upgrade head` to completion *before* traffic shifts to a new revision.
- **Env**: from Secret Manager (§5); `ENVIRONMENT=production`, `COOKIE_SECURE=true`,
  `MAILBOX_ENCRYPTION_REQUIRED=true`, explicit `CORS_ORIGINS`, `APP_BASE_URL`
  (SPA URL, for reset links).

## 3. Neon configuration

- **Isolation**: a **separate Neon project (or branch)** for staging — never the
  prod database. Neon branching makes a cheap staging branch ideal; standardise
  on **Postgres 16** (matches `pgvector/pgvector:pg16` and the prod target).
- **pgvector**: no manual step — the `vector` extension is created by Alembic
  migration `4da268d4e51a`. The migrate role needs `CREATE EXTENSION` privilege.
- **Connection**: use the Neon **pooler** endpoint; URL form
  `postgresql://USER:PASS@<pooler-host>/<db>?sslmode=require`. Store as a secret.
- **Roles (least privilege)**: a DDL-capable role for the migrate job; a
  separate runtime role for api/worker without DDL rights.
- **Migrations as a deploy gate**: api/worker must not run migrations on startup
  (`Base.metadata.create_all` is retired). Order: build image → run migrate job
  (DDL role) → on success, deploy api/worker revisions.
- **Backups**: enable Neon PITR on the staging branch; verify a restore once
  (one logical backup covers relational + pgvector data — they share the instance).

## 4. Redis configuration

- **Why required**: with `ENVIRONMENT=production`, the app **refuses to start**
  without `RATELIMIT_STORAGE_URI` (per-process in-memory limits don't hold across
  instances). Staging therefore needs Redis to boot — good parity.
- **Provider**: managed Redis (Upstash, Memorystore, or Redis Cloud), separate
  from prod. **TLS**: prefer `rediss://:PASSWORD@host:6379/0`.
- **Wiring**: set `RATELIMIT_STORAGE_URI` (secret — it embeds a password) on the
  `api` service. The worker doesn't need it.
- **Verify**: hit a rate-limited route (`/auth/login`) past its limit from one
  client and confirm a `429`; confirm limits hold across api instances if scaled.

## 5. Secrets management

- **Source of truth**: Google Secret Manager (or the platform secret store).
  **Never** in images, `.env` files in the repo, logs, or CI YAML.
- **Staging secret set** (all distinct from prod): `SECRET_KEY`, `DATABASE_URL`,
  `MAILBOX_ENCRYPTION_KEY`, `RATELIMIT_STORAGE_URI`, `GROQ_API_KEY`,
  `RESEND_API_KEY`. Non-secret config (`ENVIRONMENT`, `COOKIE_SECURE`,
  `CORS_ORIGINS`, `APP_BASE_URL`, `RESEND_FROM_EMAIL`, pool sizes) as plain env.
- **Injection**: Cloud Run secret-env references; least-privilege service account
  that can read only its own secrets.
- **`MAILBOX_ENCRYPTION_KEY`**: back up offline — losing it bricks every stored
  mailbox credential (companies must reconnect). Rotation:
  `docs/runbooks/mailbox-encryption-key.md`.
- **CI stays secret-free**: the build job uses only a dummy `SECRET_KEY`; no
  registry/cloud creds in the public workflow. Deploy creds (if CD is added)
  live in GitHub Environments/OIDC, not the workflow file.

## 6. Monitoring

- **Error tracking** (Sentry-style) on **both** api and worker: unhandled
  exceptions, draft-generation failures, SMTP/IMAP failures, migrate-job failures.
- **Uptime / probe alerts**: alert on sustained `/health/ready` 503.
- **Worker heartbeat**: the worker has no HTTP probe — alert on "no poll in N
  minutes" via `mailboxes.last_polled_at` or an emitted heartbeat metric.
- **Business/SLA metrics**: review-queue depth, drafts/min, escalation rate,
  send failures, avg confidence, Groq latency/error rate.
- **Infra metrics**: DB connection-pool saturation, slow queries, pgvector index
  health; Redis hit/latency; Cloud Run instance count / cold starts.
- **Cost/quota alerts**: Groq usage, Resend volume, Neon/Redis limits.
- **Logs**: centralised, structured, with a correlation id across api↔worker.

## 7. Health checks

| Endpoint | Type | Checks DB? | Maps to |
| --- | --- | --- | --- |
| `GET /health` | liveness | no (static) | Cloud Run liveness probe — restart a wedged container without flapping on DB blips |
| `GET /health/ready` | readiness | yes (`SELECT 1`, 503 if down) | Cloud Run startup probe — don't route traffic until the DB is reachable |

- Probe the api only; the worker is gated by `migrate` completion + has no
  ingress (monitor it via heartbeat, §6).
- Post-deploy smoke (automate in the deploy pipeline): `/health` 200,
  `/health/ready` 200, one signup→login (cookie set), KB upload→indexed, a
  draft on a seeded inbound, and one real inbound→draft→send on the dedicated
  staging mailbox.

## 8. Rollback procedure

- **Backend (api/worker)**: images are tagged by commit SHA and Cloud Run keeps
  revisions → roll back by shifting 100% traffic to the previous known-good
  revision (instant, no rebuild). Keep the last N revisions.
- **Frontend**: keep the previous `dist/` build/version; repoint the host/CDN to
  it (or redeploy the prior artifact). Invalidate the CDN cache.
- **Database / migrations**: the risky axis. Policy: **forward-compatible
  migrations** (new code works with old schema during the rollout window) so a
  code rollback needs no schema change. Only if a migration must be reverted, run
  its Alembic `downgrade` from a migrate job — and confirm each migration's
  downgrade is reversible *before* deploying it. Restore from Neon PITR only as a
  last resort (data loss between snapshot and now).
- **Redis**: stateless for rate limits — flushing/replacing the instance is safe
  (counters rebuild). No rollback concern.
- **Secrets**: rotating `SECRET_KEY` invalidates all sessions (forced re-login) —
  avoid during a rollback unless compromised.
- **Decision rule**: if `/health/ready` stays red or error-rate alerts fire after
  a deploy, roll back the api/worker revision first (fast), then investigate;
  only touch the schema if the migration itself is implicated.

---

## Suggested staging bring-up order

1. Provision Neon (staging branch, pg16) + managed Redis (TLS).
2. Put secrets in Secret Manager.
3. Build/push image by SHA (CI already validates the build).
4. Run the `migrate` job (DDL role) → success.
5. Deploy `worker`, then `api`; attach probes; map HTTPS domains.
6. Build + deploy the SPA with `VITE_API_BASE_URL`.
7. Wire monitoring + alerts.
8. Run the post-deploy smoke (§7), incl. a real inbound→draft→send on the
   dedicated staging mailbox.
9. Rehearse a rollback (shift api traffic to a prior revision) before declaring
   staging ready.
