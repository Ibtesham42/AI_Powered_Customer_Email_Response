# DevOps Engineer

Owns containerization, environments, deployment, CI/CD, and observability.

## Responsibilities

- Docker / Docker Compose for local dev and the deployment images
  (`docker-compose.yml` local, `docker-compose.prod.yml` + Caddy for a VPS).
- Deployment: the **active pilot is zero-budget — own PC + Tailscale Funnel**
  (`docs/runbooks/zero-budget-pilot.md`; $0, no credit card, must allow
  outbound IMAP/SMTP — verify any new host with `deploy/hf-probe/`). Cloud Run
  + Cloud SQL remains the long-term scale target.
- CI/CD: GitHub Actions (`lint-test` + `docker-build` jobs); lint, type-check,
  test, image build + no-secret smokes on every push/PR.
- Logging, health probes, and monitoring (Sentry, worker heartbeat).

## Coding standards

- One Dockerfile per deployable (`api`, `worker`); multi-stage builds, slim
  base images, non-root runtime user.
- `docker-compose.yml` for local dev: `api`, `worker`, `postgres` (with
  pgvector). One command brings the stack up.
- Pin dependency versions. `requirements.txt` is split or locked so builds are
  reproducible.
- `.env.example` lists every required variable; real `.env` is git-ignored.

## Architecture rules

- `api` and `worker` are separate processes/containers sharing the codebase —
  never run the worker loop inside the API process.
- No build-time secrets baked into images; secrets injected at runtime
  (Cloud Run env / Secret Manager).
- Local Postgres mirrors production (Cloud SQL) — same major version, pgvector
  available in both.
- Schema changes apply via an Alembic migration step in the deploy pipeline,
  not by app startup.

## Best practices

- CI on every push: `ruff`, `black --check`, `mypy`, `pytest`. Block merge on
  failure.
- Images tagged by commit SHA; deployments are reproducible and rollback-able.
- `venv/` is never copied into an image or scanned in CI.
- Separate `dev` / `staging` / `prod` configs and databases.

## Security requirements

- Secrets from Secret Manager / runtime env only — never in images, logs, or
  git.
- Least-privilege service accounts; the app's cloud identity can reach only
  what it needs.
- Cloud SQL reachable only over private IP / connector, not the public
  internet.
- Dependency and image vulnerability scanning in CI.

## Performance requirements

- Health endpoints: `/health` (liveness) and `/health/ready` (readiness —
  checks DB). Configure probes against them.
- Mind Cloud Run cold starts — the embedding model makes the container heavy;
  consider min-instances for the worker or a lighter embedding path.
- Right-size DB connection pools to the instance count.
- Centralised structured logs with correlation ids; alert on error-rate spikes.
