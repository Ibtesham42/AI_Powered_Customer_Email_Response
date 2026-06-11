---
title: ai-customer-support-api
emoji: 📧
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# AI Customer Support — API + worker Space

Runs the FastAPI api and the background worker as two processes in one
container (`start.sh`). All state lives off the Space: Postgres+pgvector on
Neon, rate-limit counters on Upstash, raw KB files are re-uploadable. Plan and
limits: `docs/runbooks/zero-budget-pilot.md` in the app repo.

> The YAML header above is required Space metadata (`app_port: 8000` tells HF
> where uvicorn listens). Keep it at the top of the Space's root README.

## Deploying the Space from the app repo

The Space builds from **its own** git repo's root `Dockerfile`. Publish a
branch where this folder's files sit at the root:

```bash
# from the app repo root
git checkout -b hf-space
cp deploy/hf-space/Dockerfile Dockerfile
cp deploy/hf-space/start.sh start.sh
cp deploy/hf-space/README.md README.md     # branch-local overwrite, intentional
git add Dockerfile start.sh README.md
git commit -m "hf-space deployment variant"

# one-time: create a (private) Docker Space on huggingface.co, then
git remote add hf https://huggingface.co/spaces/<user>/<space>
git push hf hf-space:main --force          # HF builds + starts it
git checkout main                          # keep working on main as usual
```

Re-deploying after app changes: `git checkout hf-space && git merge main &&
git push hf hf-space:main`.

## Space secrets (Settings → Variables and secrets)

Same production set as any deploy — values are injected as env vars:

| Secret | Value |
|---|---|
| `SECRET_KEY` | fresh random (not the dev one) |
| `DATABASE_URL` | Neon **pooler** URL (`...?sslmode=require`) |
| `MAILBOX_ENCRYPTION_KEY` | fresh Fernet key — **back up offline first** |
| `MAILBOX_ENCRYPTION_REQUIRED` | `true` |
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | **`none`** (hf.space is cross-site with the SPA) |
| `CORS_ORIGINS` | the SPA origin, e.g. `https://<project>.pages.dev` |
| `APP_BASE_URL` | the SPA origin (password-reset links) |
| `POLL_INTERVAL_SECONDS` | `600` (Neon free tier — see runbook §4) |
| `RATELIMIT_STORAGE_URI` | Upstash `rediss://...` URL (it embeds the password) |
| `GROQ_API_KEY` / `RESEND_API_KEY` | as usual |
| `SENTRY_DSN` / `WORKER_HEARTBEAT_URL` | monitoring (free tiers) |

## First-start expectations

- Build is slow (torch wheels) and the image is large — normal.
- On the worker's first cycle it downloads the BGE model (~400 MB) into the
  ephemeral cache; after any Space restart it re-downloads. First draft may
  take a few extra minutes.
- Verify: `https://<user>-<space>.hf.space/health` → `{"status":"ok"}` and
  `/health/ready` → `{"status":"ready"}` (Neon reachable).
- Keep-alive: point UptimeRobot at `/health` (5-min interval) or the free
  Space sleeps after 48 h without HTTP traffic.
