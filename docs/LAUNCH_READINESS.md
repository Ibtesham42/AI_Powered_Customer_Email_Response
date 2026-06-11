# Launch-Readiness Report

_AI Customer Support SaaS — assessed 2026-06-11, after Phase 7 (production
hardening) merged to `main` and a live end-to-end workflow test.
**Updated 2026-06-11 (later same day):** Docker build validated in CI; full CI
pipeline green._

## TL;DR verdict

**Ready for staging deployment and a single-company pilot; not yet ready for
general availability.** Every application-layer blocker from the
production-readiness audit (Critical + High) is closed, the full customer-support
workflow was verified live (Neon Postgres + pgvector, real Groq, real Gmail
IMAP/SMTP), and the container build path is now **validated by CI on every
push** (image builds on Linux; the app imports cleanly inside it; pytest suite
green on a clean-install runner). What remains is **operational**: no staging/
production environment is provisioned yet, and there is no error
monitoring/alerting. Those are deployment tasks, not code defects.

**Recommendation: execute the staging plan now**
(`docs/runbooks/staging-deployment.md`) — stand up staging, wire monitoring, run
the pilot-readiness checklist, then a single friendly-company pilot. Open to
more companies only after the pilot survives 1–2 weeks of real traffic.

### CI validation outcome (2026-06-11)

- **Docker build: VALIDATED.** The `docker-build` job builds `./Dockerfile` on
  `ubuntu-latest` on every push/PR and fails CI if the image can't build. First
  green run: `27325158511`. All three no-infra smokes pass, including the heavy
  `import backend.main` (proves the torch/sentence-transformers wheels load in
  the clean Linux image).
- **Test suite on a clean runner: VALIDATED.** The CI pytest failure was
  diagnosed (the repo's `backend`/`app` packages are not pip-installed; bare
  `pytest` doesn't put the repo root on `sys.path` the way `python -m pytest`
  does) and fixed properly via `pythonpath = ["."]` in `pyproject.toml` plus
  `ENV PYTHONPATH=/app` in the Dockerfile so every container entrypoint imports
  consistently. `lint + test (SQLite)` green from run `27334053401` (63 tests).
- Test-critical deps are now pinned (`httpx`, `pytest`, `pytest-asyncio`, etc.)
  so a clean CI install reproduces the local environment.

---

## 1. Remaining blockers

Ranked by what would actually bite a real customer.

| # | Blocker | Severity | Status / action |
|---|---------|----------|-----------------|
| B-1 | **Container image never built or run.** | ~~High~~ | **✅ RESOLVED (2026-06-11).** CI `docker-build` job builds the image on `ubuntu-latest` on every push/PR and runs no-infra smokes (config import, alembic wiring, full `import backend.main` incl. the ML stack). Fails the workflow on any build break. Residual (folded into staging): the image hasn't yet been *run as a long-lived service* against real infra — the staging deploy is that test. |
| B-2 | **No staging/production environment provisioned.** No Cloud Run/Cloud SQL, no managed Redis, no domain/TLS, no Secret Manager wiring. | **High** | Execute `docs/runbooks/staging-deployment.md` (plan is written; not yet implemented). |
| B-3 | **No error monitoring / alerting.** | ~~High~~ | **✅ Code RESOLVED (Phase 8 chunk 1):** optional Sentry init in api+worker (fail-soft, no PII) + worker dead-man heartbeat (`WORKER_HEARTBEAT_URL`). Remaining: create the Sentry project / Healthchecks.io check / UptimeRobot monitor and set the env vars at deploy. |
| B-4 | **Inbound email roundtrip unverified end-to-end.** The live test injected the inbound email as synthetic data; `poll_mailboxes` fetches *all unread* mail and marks it read, so it must not run against a shared/personal inbox. | **Medium** | Verify a real inbound→draft roundtrip on a **dedicated** throwaway support mailbox before pilot. |
| B-5 | **Send is not idempotent.** | ~~Medium~~ | **✅ RESOLVED (Phase 8 chunk 2):** atomic REVIEWED→SENDING claim — duplicates/concurrent sends 409; SMTP failure releases the claim (502, safe manual retry). No auto-retry by design (ambiguous SMTP timeouts may have delivered). |
| B-6 | **No KB upload size/count caps.** | ~~Medium~~ | **✅ RESOLVED (Phase 8 chunk 3):** streamed file-size cap (413), per-Company document quota (409), FAQ length caps (422). Env-tunable. |
| B-7 | **Frontend cut-over undecided.** The Vite+React SPA is at feature parity but the legacy Streamlit dashboard is still present; the cut-over (retire Streamlit) is deferred. | **Low** | Pick the production UI; if SPA, complete cut-over and stop shipping Streamlit. |
| B-8 | **CI lint/format non-blocking + transient `400` seen once on `PUT /messages/{id}/draft`.** Quality/observability follow-ups, not launch-stoppers. | **Low** | Normalize lint baseline → make blocking; add response-body logging to catch the transient 400 if it recurs. |

**Already resolved this cycle:** mailbox encryption key configured; pending
migration `a1b2c3d4e5f6` (`token_version`) applied to Neon; refresh-token cookie +
in-memory access token; Redis rate-limit prod fail-fast; SSRF guard; mailbox-key
fail-fast; **B-1 container build validated in CI**; **CI pytest failure root-caused
(sys.path/package discovery, not deps) and fixed** — full pipeline green.

---

## 2. Production deployment steps

Target: **Google Cloud Run (api + worker) + Cloud SQL Postgres 16 w/ pgvector +
managed Redis**. See `docs/runbooks/deployment.md` for the compose/runbook detail.

1. **Provision data stores.** Cloud SQL Postgres **16** (matches local
   `pgvector/pgvector:pg16`), private IP only; managed Redis (TLS, `rediss://`).
   Enable Cloud SQL automated backups + point-in-time recovery.
2. **Secrets → Secret Manager.** `SECRET_KEY`, `DATABASE_URL`,
   `MAILBOX_ENCRYPTION_KEY`, `RATELIMIT_STORAGE_URI`, `GROQ_API_KEY`,
   `RESEND_API_KEY` (never in env files or images).
3. **Build & push image**, tagged by commit SHA (resolve B-1 first). One image,
   three commands (api / worker / migrate).
4. **Run migrations as a pre-deploy gate.** A Cloud Run Job (or CI step) running
   `alembic upgrade head` with a **DDL-capable** role, to completion, *before*
   routing traffic. Never migrate on app startup.
5. **Deploy `api`** with a least-privilege runtime DB role, `ENVIRONMENT=production`,
   `COOKIE_SECURE=true`, explicit `CORS_ORIGINS`, behind HTTPS. Startup probe →
   `/health/ready`; liveness probe → `/health`.
6. **Deploy `worker`** (min-instances ≥ 1 so polling/draining runs continuously;
   it self-heals on crash and shuts down cleanly on SIGTERM). Set smaller pool:
   `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=2`.
7. **DNS + TLS** for the API and the SPA origin; confirm HSTS is emitted in prod.
8. **Smoke test in staging**: signup/login (cookie flow), KB upload→indexed,
   mailbox connect on a dedicated inbox, real inbound→draft→approve→send, audit
   rows. Then pilot.

---

## 3. Environment variables checklist

`SECRET_KEY` fails fast at import if missing. Per-company support mailboxes are
connected at runtime via the API, **not** env. (`EMAIL_USER`/`EMAIL_PASS` are
legacy standalone-app only — do **not** set them in the backend deploy.)

### Required in production
- [ ] `SECRET_KEY` — strong random; Secret Manager
- [ ] `DATABASE_URL` — Cloud SQL Postgres 16 + pgvector, private IP, `sslmode=require`
- [ ] `GROQ_API_KEY` — required for AI replies
- [ ] `ENVIRONMENT=production` — enables Secure cookie + HSTS
- [ ] `RATELIMIT_STORAGE_URI` — managed Redis (`rediss://…`); **app refuses to start without it in prod**; treat as a secret (may embed a password)
- [ ] `MAILBOX_ENCRYPTION_KEY` — Fernet key; **back up offline**
- [ ] `MAILBOX_ENCRYPTION_REQUIRED=true` — refuse to start without a valid key
- [ ] `COOKIE_SECURE=true` — HTTPS-only refresh cookie
- [ ] `CORS_ORIGINS` — explicit SPA origin(s); never `*`
- [ ] `APP_BASE_URL` — public frontend URL (password-reset links)
- [ ] `RESEND_API_KEY` + `RESEND_FROM_EMAIL` — password-reset email; `FROM` on a verified domain

### Recommended / tunable (sensible defaults exist)
- [ ] `COOKIE_SAMESITE` — `lax` (same-origin) or `none` (separate-origin; needs Secure)
- [ ] `COOKIE_DOMAIN`, `REFRESH_COOKIE_NAME` — for cross-subdomain deploys
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` (30), `REFRESH_TOKEN_EXPIRE_DAYS` (30)
- [ ] `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` (worker: 2 / 2 / 1800)
- [ ] `LOG_LEVEL` (INFO), `JWT_ALGORITHM` (HS256)
- [ ] `MODEL_NAME`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT`, `LLM_PROVIDER`
- [ ] `ESCALATION_CONFIDENCE_THRESHOLD` (40), `ESCALATION_MAX_REPLIES` (2)
- [ ] `RESET_TOKEN_EXPIRE_MINUTES` (30)

---

## 4. Backup & recovery checklist

- [ ] **Cloud SQL automated backups + PITR** enabled (covers relational **and**
      pgvector data in one logical backup — they share the instance).
- [ ] **`MAILBOX_ENCRYPTION_KEY` backed up offline** in a second secure location.
      If lost, **every stored mailbox credential is unrecoverable** — companies
      must reconnect. Rotation/recovery procedure: `docs/runbooks/mailbox-encryption-key.md`.
- [ ] **`SECRET_KEY` custody** documented; rotating it invalidates all active
      access/refresh tokens (all users re-login) — plan rotation windows.
- [ ] **Restore drill**: actually restore a backup into a scratch DB and run
      `alembic current` + a read query before trusting backups.
- [ ] **Migration rollback path**: confirm each migration's downgrade, or document
      the forward-fix policy.
- [ ] **Disaster runbook**: who rotates which secret, where backups live, RTO/RPO.

---

## 5. Monitoring checklist

Currently present: structured logging, `/health` (liveness), `/health/ready`
(DB readiness), audit log. Missing for a real SaaS:

- [ ] **Error tracking** (Sentry-style) on both `api` and `worker` — unhandled
      exceptions, draft-generation failures, SMTP/IMAP failures. _(B-3)_
- [ ] **Uptime + probe alerting** on `/health/ready` (paged on sustained 503).
- [ ] **Worker liveness signal** — it has no HTTP probe; alert on "no poll in N
      minutes" via `mailboxes.last_polled_at` or a heartbeat metric.
- [ ] **Business/SLA metrics**: review-queue depth, drafts/min, escalation rate,
      send failures, avg confidence, Groq latency/error rate.
- [ ] **DB metrics**: connection-pool saturation, slow queries, pgvector index
      health/bloat, storage growth.
- [ ] **Rate-limit + auth metrics**: 429s, failed-login spikes (enumeration/abuse).
- [ ] **Cost/quota alerts**: Groq usage, Resend volume, Cloud SQL/Redis limits.
- [ ] **Log aggregation** with correlation IDs across api↔worker.

---

## 6. Post-launch recommendations

- **Harden the deferred audit Medium/Low items** in priority order: send
  idempotency + retry (B-5), KB upload caps (B-6), list-endpoint pagination,
  signup email-enumeration hardening, audit-coverage gaps.
- **Finish the SPA cut-over** and retire the legacy Streamlit dashboard (B-7).
- **Make CI lint/format blocking**: normalize the pre-existing format drift
  (`black .` + `ruff --fix .`), then flip `ruff`/`black` to blocking; add image
  CVE scanning (Trivy) and pin base images by digest (C2 follow-ups).
- **Scale posture**: add PgBouncer / Cloud SQL pooler if instance count grows;
  right-size pools to the DB connection cap; consider min-instances for the worker.
- **Tighten least privilege**: enforce the runtime-vs-migrate DB role split in IaC;
  least-privilege cloud IAM.
- **Embedding-model immutability**: the KB is `vector(768)` (BGE-base) — a model
  swap is a migration + re-embed, not a config flip. Document this.
- **Per-company onboarding**: each company needs its own dedicated support mailbox
  + App Password; document the connect flow and the Gmail App-Password setup.
- **Cost & latency**: monitor Groq spend and consider a lighter embedding path /
  image slimming (CPU-only torch) to cut cold-start and image size.

---

## 7. What was verified live (evidence basis)

All on the live stack (Neon + Groq + Gmail), 2026-06-11:

- Boot + `/health` 200; `/health/ready` 200 (real `SELECT 1` on Neon).
- Security headers present (nosniff / frame-DENY / referrer-policy); HSTS off in dev.
- H1 cookie auth: login sets httpOnly `acs_refresh_token`; cookie-only refresh;
  logout clears it; bearer `/user/me` 200.
- Full workflow (11/11 PASS): mailbox connect (live IMAP+SMTP) → KB upload →
  pgvector ingest → retrieval (sim 0.75) → ingest → ticket → message → Groq draft
  (intent=refund_request, confidence 80) → review queue → edit → real SMTP send →
  audit (5 actions). Credential stored encrypted (Fernet), not plaintext.

Verified later the same day, in CI on Linux runners:

- **Docker image build** (multi-stage, non-root, full ML stack) + no-infra
  runtime smokes — green, enforced on every push/PR.
- **pytest suite (63 tests) on a clean-install runner** — green after the
  package-discovery fix (`pythonpath` in pyproject + `PYTHONPATH=/app` in the
  image).

**Not yet verified:** the image *running as a service* (docker-compose stack /
Cloud Run), managed Redis rate-limiting in prod, separate-origin cookie flow,
real inbound IMAP roundtrip, behaviour under load. All are exercised by the
staging plan (`docs/runbooks/staging-deployment.md`).
