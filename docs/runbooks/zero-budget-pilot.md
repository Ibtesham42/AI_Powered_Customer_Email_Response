# Zero-Budget Pilot Deployment ($0/month, no credit card)

_Plan for a validation/pilot launch with no hosting spend **and no credit
card** (constraint added 2026-06-11 — this supersedes the earlier Oracle
Always Free plan in this file; Oracle requires a card at signup). The Hetzner
path in `docs/DEPLOYMENT_STRATEGY.md` remains the upgrade once ~$9/mo is
acceptable; §5 keeps that switch a DNS-flip._

## Why most providers are out

The app needs ~**1.5–2 GB RAM per process** (api *and* worker import
torch + the BGE embedding model) and an **always-on worker**. Combined with
"no card":

| Provider | No-card free tier? | Verdict |
|---|---|---|
| Oracle Always Free | ❌ card for identity | out |
| Fly.io | ❌ card at signup | out |
| Railway | ❌ one-time trial, then card | out |
| Koyeb | ❌ card verification (and 512 MB anyway) | out |
| Northflank | ❌ card verification | out |
| Render | ✅ no card — **but** 512 MB (torch OOMs) + free services sleep + workers are paid-only | out for this codebase |
| GCP / AWS / Azure | ❌ card | out |
| PythonAnywhere / Replit | ✅/✅ — but tiny CPU/RAM, no Docker, no real worker | out |
| **Hugging Face Spaces (Docker)** | ✅ **no card; free CPU Space = 2 vCPU / 16 GB RAM** | ✅ **the pick** |
| **Own PC + Cloudflare Tunnel** | ✅ no card (but a named tunnel needs a domain, ~$10/yr) | fallback |

Neon, Cloudflare Pages, Upstash Redis, Groq free, Resend free, Sentry,
UptimeRobot, Healthchecks.io — all usable **without a card**. ✅

## 1. Architecture

```
 browser ─▶ Cloudflare Pages (SPA, <project>.pages.dev or app.<domain>)   $0
               │  cross-site → COOKIE_SAMESITE=none + COOKIE_SECURE=true
               ▼
 Hugging Face Docker Space (free CPU: 2 vCPU / 16 GB / ~50 GB ephemeral)  $0
 https://<user>-<space>.hf.space  (TLS provided by HF)
 ┌────────────────────────────────────────────┐
 │ ONE container, TWO processes (start.sh):   │──▶ Neon Postgres+pgvector $0
 │   uvicorn backend.main:app  (api, :8000)   │──▶ Upstash Redis (TLS)    $0
 │   python scripts/email_worker.py (worker)  │──▶ Groq free · Resend free$0
 └────────────────────────────────────────────┘
 Monitoring: Sentry · Healthchecks.io · UptimeRobot (pings ALSO keep the
 Space awake — it sleeps after 48 h without HTTP traffic)                 $0
```

Same principle as before: **all state lives off the compute** (Neon for data,
Upstash for counters, HF rebuilds the image from the repo). The Space's disk is
ephemeral — uploaded raw KB files vanish on restart, but the embedded chunks
live in pgvector, so retrieval is unaffected (re-upload only to re-ingest).

What changes vs. the repo's compose model: the api and worker run as **two
processes in one container** via a small `start.sh` (a deployment adaptation —
they remain separate processes; the "never run the worker loop inside the API
process" rule is intact). Redis moves to Upstash (`rediss://`) because a Space
is one container. `docker-compose.prod.yml` stays the artifact for the
VPS/Hetzner path.

The deployment files exist in **`deploy/hf-space/`** (Space Dockerfile
mirroring the root one + `start.sh` + Space README with metadata and the full
secrets table) — no application code changes. Deploy by publishing the
`hf-space` branch (those files copied to the repo root) to the Space remote;
exact commands are in `deploy/hf-space/README.md`.

## 2. Setup sequence

1. **Accounts (no card):** huggingface.co, Upstash, and (if not already)
   Neon / Cloudflare / Groq / Resend / Sentry / Healthchecks.io / UptimeRobot.
2. **Day-one feasibility check (do this FIRST):** deploy the ready-made probe
   in **`deploy/hf-probe/`** (3 files, stdlib-only, builds in ~1 min) to a
   throwaway Docker Space. It verifies **outbound IMAP (993) + SMTP (465)** to
   Gmail and serves a JSON `PASS`/`FAIL` verdict — interpretation guide in its
   README. HF allows general egress, but SMTP is the classic thing platforms
   block — if FAIL, this plan is dead and the fallback (§ "own PC + tunnel")
   applies. Everything else only matters if this passes.
3. **Upstash Redis:** create a free database → copy the `rediss://` URL
   (treat as a secret) → it becomes `RATELIMIT_STORAGE_URI`.
4. **Create the real Space** (Docker SDK, private repo or mirror of this one
   with the Space files). Set **Space secrets** (HF's env-var store): the same
   production set as ever — `SECRET_KEY`, `DATABASE_URL` (Neon pooler),
   `MAILBOX_ENCRYPTION_KEY` (backed up offline), `MAILBOX_ENCRYPTION_REQUIRED=true`,
   `ENVIRONMENT=production`, `COOKIE_SECURE=true`, **`COOKIE_SAMESITE=none`**,
   `CORS_ORIGINS=https://<spa-origin>`, `APP_BASE_URL=https://<spa-origin>`,
   `POLL_INTERVAL_SECONDS=600`, `RATELIMIT_STORAGE_URI` (Upstash),
   `GROQ_API_KEY`, `RESEND_API_KEY`, `SENTRY_DSN`, `WORKER_HEARTBEAT_URL`.
5. **Frontend:** Cloudflare Pages from the GitHub repo
   (`frontend/`, `npm ci && npm run build`, `dist/`,
   `VITE_API_BASE_URL=https://<user>-<space>.hf.space`).
6. **Keep-alive + monitoring:** UptimeRobot on `https://…hf.space/health` and
   `/health/ready` every 5 min (doubles as the anti-sleep ping);
   Healthchecks.io check wired to `WORKER_HEARTBEAT_URL`; Sentry DSN set.
7. **Verify** with the staging checklist: cookie login (cross-site — confirm
   the `SameSite=None; Secure` cookie round-trips), rate-limit 429 (Upstash),
   KB upload → indexed, and the real inbound→draft→approve→send roundtrip on a
   dedicated pilot mailbox (B-4).

## 3. Compromises vs. the paid plans

| Compromise | Impact |
|---|---|
| Two processes in one container | None functionally; restart restarts both. |
| `hf.space` subdomain (no custom domain on free Spaces) | Cross-site cookies → `SameSite=none` (supported in config); the API URL looks like a demo, not a product — acceptable for a pilot. |
| 48-h inactivity sleep | Neutralised by UptimeRobot pings; a sleep+cold start would take minutes (image pull + torch import). |
| Ephemeral disk | Raw KB files lost on restart (chunks safe in Neon); re-upload to re-ingest. |
| No SLA; HF may restart/rebuild Spaces | Worker resumes via the queue (`awaiting_ai` rows persist); minutes of downtime possible at random. |
| ToS greyness | Free Spaces are meant primarily for ML demos/apps; a low-traffic AI-support pilot is ML-adjacent but not a classic demo. Risk: HF asks you to upgrade/move. Mitigation: low traffic, honest naming, be ready to move (state is off-box). |
| SMTP/IMAP egress unverified | **Hard gate** — checked in step 2 before any other work. |
| `POLL_INTERVAL_SECONDS=600` | Unchanged from the previous plan (Neon free compute-hours); ≤10-min email pickup. |
| Groq free tier | ~500–1,000 drafts/day ceiling, queue absorbs bursts (unchanged). |

## 4. Expected limits (unchanged from the Oracle plan)

~**5–15 companies**, ~**500–1,000 drafts/day** (Groq free), ~**100 MB KB text**
total (Neon 0.5 GB), Resend 100/day (resets only). Compute is ample
(16 GB RAM); the binding constraints are Neon compute-hours (hence the 600 s
poll) and Groq's free-tier rate limits.

## Fallback: own PC + Cloudflare Tunnel

If HF blocks mail egress (step 2 fails) or the Space proves too flaky: run the
stack on your own always-on PC — natively in the venv (as the live e2e test
already did) or via compose — and publish it with **Cloudflare Tunnel** (free,
no card, no port-forwarding, hides your IP). Honest catch: a *stable named*
tunnel hostname requires a domain in your Cloudflare account (~$10/yr — money,
but not monthly and not a card-on-file subscription… it does need a payment
method, e.g. PayPal works on some registrars). Without any domain, tunnel URLs
are ephemeral — unusable for a pilot. Other tradeoffs: your PC's uptime is the
SLA, residential bandwidth, electricity.

## 5. Migration path (HF Space → Hetzner, when budget exists)

Identical in spirit to before — **no data migrates**:
1. Provision the VPS, copy `.env`, `docker compose -f docker-compose.prod.yml
   up -d --build` (the compose path was built for exactly this).
2. Point the SPA's `VITE_API_BASE_URL` at the new `api.<domain>` (one Pages
   env change + rebuild), set `COOKIE_SAMESITE=lax` (same-site again),
   update `CORS_ORIGINS`/`APP_BASE_URL`.
3. Re-point UptimeRobot/Healthchecks; pause the Space.
Effort ≈ an hour; Neon/Upstash/Groq/Resend/Sentry unchanged (drop Upstash for
on-box redis if you prefer).
