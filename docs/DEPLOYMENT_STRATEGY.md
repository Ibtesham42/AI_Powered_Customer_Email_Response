# Deployment Strategy & Launch Plan (lowest-cost public launch)

_Plan only — nothing implemented. Assessed 2026-06-11 against the current
codebase: FastAPI api + always-on worker sharing one Docker image (CI-validated),
Neon Postgres + pgvector, in-process BGE embeddings (CPU fallback), Groq LLM,
per-company Gmail IMAP/SMTP, Vite/React SPA, Redis-backed rate limiting
(required in prod). Companion docs: `LAUNCH_READINESS.md`,
`runbooks/staging-deployment.md`, `runbooks/deployment.md`._

## The two facts that drive every hosting decision

1. **RAM floor.** Both processes import torch + sentence-transformers; the
   worker loads BGE for retrieval and the **API also loads it** (KB ingestion
   embeds in-process via a background task). Realistic floor: **~1.5–2 GB per
   process** on CPU. This kills every 512 MB free tier (Render free, fly
   256 MB machines).
2. **Always-on worker.** `email_worker.py` polls every 10 s. Platforms that
   sleep idle services (Render free, Cloud Run scale-to-zero) break it, and the
   constant polling keeps the database compute awake 24/7.

## 1. Recommended production architecture

```
                       ┌────────────────────────────┐
   users (agents/owners)│  Cloudflare (free)         │
        browser ───────▶│  DNS + app.domain.com      │
                       │  Pages: Vite/React SPA     │
                       └────────────┬───────────────┘
                                    │ https (same-site subdomain,
                                    │  SameSite=lax cookie + CORS)
                       ┌────────────▼───────────────┐
                       │ api.domain.com             │
                       │ VPS (Hetzner) — Docker     │
                       │ ┌────────┐  ┌───────────┐ │
                       │ │ Caddy  │─▶│ api       │ │   ┌──────────────┐
                       │ │ (TLS)  │  │ (uvicorn) │─┼──▶│ Neon Postgres │
                       │ └────────┘  └───────────┘ │   │ + pgvector    │
                       │ ┌───────────┐ ┌─────────┐ │   └──────────────┘
                       │ │ worker    │ │ redis   │ │
                       │ │ (poll/AI) │ │ (rate-  │ │   ┌──────────────┐
                       │ └─────┬─────┘ │  limit) │ │──▶│ Groq API      │
                       └───────┼───────┴─────────┘     └──────────────┘
                               │ IMAP/SMTP                ┌────────────┐
                               ▼                          │ Resend     │
                    each Company's Gmail mailbox          │ (pw resets)│
                    (App Password, Fernet-encrypted)      └────────────┘

   Monitoring: Sentry (errors, api+worker) · UptimeRobot (/health/ready)
               · Healthchecks.io (worker heartbeat) — all free tiers
```

This is exactly the topology the repo already models in `docker-compose.yml`
(api/worker/redis/migrate), with the `db` service swapped for Neon and Caddy
added for TLS.

## 2. Recommended hosting stack (summary)

| Layer | Pick | Cost |
|---|---|---|
| Frontend | **Cloudflare Pages** | $0 (unlimited bandwidth, commercial OK) |
| Backend (api+worker+redis) | **Hetzner VPS CX32 (4 vCPU/8 GB)** via the existing compose | ~$8/mo |
| Database | **Neon** (stay) — free → Launch $19 | $0–19/mo |
| Redis | compose container on the VPS | $0 |
| LLM | **Groq** pay-as-you-go | ~$0.001–0.002/draft |
| Transactional email | **Resend** free (3k/mo, 100/day) | $0 |
| Errors | **Sentry** free (5k events/mo) | $0 |
| Uptime/heartbeat | **UptimeRobot** + **Healthchecks.io** free | $0 |
| Domain/DNS/TLS | **Cloudflare Registrar** + DNS; Caddy auto-TLS | ~$10/yr |

## 3. Free-tier-only option ($0/mo + domain)

> **Now the active pilot plan** — full architecture, setup guide, limits, and
> the migration path back to Hetzner live in
> `docs/runbooks/zero-budget-pilot.md` (budget constraint, 2026-06-11).

**Oracle Cloud Always Free** is the only free compute that fits the RAM floor:
4 ARM Ampere cores + 24 GB RAM, free forever. Run the whole compose stack on it;
Neon free for DB; Cloudflare Pages; Upstash Redis free (or compose redis); free
monitoring tier.

Honest caveats: requires an **arm64 image build** (torch aarch64 wheels exist;
CI builds amd64 today — would need a buildx multi-arch addition); capacity in
popular regions is scarce; Oracle has a documented history of reclaiming idle
Always-Free instances and weak support. Acceptable for a pilot you watch
closely; I would not bet paying customers' mailboxes on it.

**Neon free-tier nuance:** the 10 s worker poll keeps compute awake 24/7. At the
0.25 CU minimum that's ≈ 186 compute-hours/month vs the 191.9 free allowance —
it *just* fits, with zero headroom for the api's own queries at busier moments.
Expect to need Launch ($19/mo) soon after real traffic starts, or set the
env-tunable `POLL_INTERVAL_SECONDS=600` so Neon autosuspends between cycles
(see `runbooks/zero-budget-pilot.md` §4).

## 4. Lowest-cost production-ready option (recommended)

**One Hetzner VPS + the existing docker-compose + Neon + Cloudflare Pages.**

- Hetzner **CX22** (2 vCPU/4 GB, ~$4.50/mo) is the absolute floor — tight with
  both processes loading the ML stack (~2 GB each worst-case). **CX32**
  (4 vCPU/8 GB, ~$8/mo) is the safe pick and my recommendation.
- The repo's compose file already orchestrates api/worker/redis/migrate with
  healthchecks, restart policies, and migrate-as-deploy-gate. Production deltas
  (a small `docker-compose.prod.yml`: drop the `db` service, point
  `DATABASE_URL` at Neon, add Caddy) are config, not architecture.
- Total: **~$9/mo** infra + Groq usage + $10/yr domain.

## 5. Backend hosting comparison

| Platform | Fit | ~Cost (api+worker) | Pros | Cons |
|---|---|---|---|---|
| **Hetzner/VPS + compose** ✅ | Best | **$4.50–8/mo** | Cheapest by 3–6×; compose already written; no platform image limits; redis free on-box | You own ops (patches, TLS via Caddy, backups of nothing local — DB is Neon); single-node SPOF |
| **Fly.io** | Good | ~$21/mo (2× shared-cpu 2 GB) | Per-second billing, volumes, good DX, easy multi-region | No real free tier anymore; multi-GB image = slow deploys |
| **Railway** | OK | ~$25–45/mo | Simplest DX, compose-like services | RAM-based pricing punishes the ML stack (2 always-on 2 GB processes) |
| **Render** | Poor | ~$50/mo (2× Standard 2 GB) | Simple | Free tier sleeps (kills worker) and 512 MB starter OOMs on torch; priciest |
| **Cloud Run** | Poor *for this code* | ~$40–60/mo | Best autoscaling, the long-term target in the runbooks | Worker needs min-instances=1 (always-billed); 30–60 s cold starts with a multi-GB torch image make scale-to-zero unusable for the api |
| **Oracle Always Free** | Free | $0 | 24 GB RAM free | arm64 rebuild, capacity lottery, reclamation risk |

Cloud Run becomes the right answer **after** the deferred image-slimming
(CPU-only torch) or moving embeddings out-of-process — not before.

## 6. Frontend hosting

**Cloudflare Pages** ✅ — free tier explicitly allows commercial use, unlimited
static bandwidth, 500 builds/mo, custom domains + TLS, deploys from the GitHub
repo (`frontend/` build: `npm ci && npm run build`, output `dist/`).
- Vercel: best DX but the **Hobby tier prohibits commercial use** → you'd owe
  $20/user/mo immediately. Skip.
- Netlify: fine, 100 GB bandwidth free; no advantage over CF Pages here.

Cookie note: serve the SPA at `app.domain.com` and the API at `api.domain.com`.
These are **same-site** (same registrable domain), so the existing
`SameSite=lax` httpOnly refresh cookie works as-is — no `SameSite=none` needed —
with `CORS_ORIGINS=https://app.domain.com` (CORS still applies cross-origin).

## 7. Database

**Stay on Neon.** It's already wired (pooler URL, pgvector via Alembic,
PITR available), pg16-compatible, and the free→$19→$69 ladder matches growth.
Migrating to RDS/Cloud SQL adds cost (smallest Cloud SQL ≈ $10–30/mo) for zero
feature gain at this scale. Watch: storage (0.5 GB free — KB chunks at ~3 KB/
vector + HNSW overhead ≈ low-100k chunks) and the compute-hours math in §3.
Use the **pooler endpoint** (worker + api pools are already env-tuned).

## 8. Redis

Rate limiting is the only Redis consumer (auth routes), so volume is tiny:
- **On the VPS: the compose `redis` container** ✅ — free, already configured
  (`RATELIMIT_STORAGE_URI=redis://redis:6379/0`), satisfies the prod fail-fast.
- On a PaaS: **Upstash free** (10k commands/day) — ample for auth-route limits;
  use `rediss://` (TLS) and treat the URL as a secret.

## 9. Secrets management

Lowest-cost sane setup: **a root-owned `.env` on the VPS (chmod 600)** loaded by
compose — plus discipline: never in git (already enforced), never in images
(already enforced by `.dockerignore`). One step up at $0: **Doppler or
Infisical free tier** as the source of truth, rendered to the server.
Non-negotiables regardless of tool:
- `MAILBOX_ENCRYPTION_KEY` backed up **offline in two places** (losing it bricks
  every stored mailbox credential — see `runbooks/mailbox-encryption-key.md`).
- Separate staging/prod values for every secret.
- CI stays secret-free (it already is).

## 10. Monitoring & error tracking

All free tiers; together they close launch blocker B-3:
- **Sentry (free, 5k events/mo)** — error tracking in api **and** worker.
  ⚠️ Small code change required (SDK init) — listed in the blockers.
- **UptimeRobot (free)** — external probe on `/health` + `/health/ready`,
  5-minute interval, alerts on sustained 503.
- **Healthchecks.io (free, 20 checks)** — dead-man switch for the worker: ping a
  check URL each poll cycle; alert when silent N minutes. ⚠️ Tiny code change
  (one HTTP ping in the worker loop).
- Logs: `docker compose logs` + journald on the VPS is fine to start; Grafana
  Cloud free if/when aggregation matters.

## 11. Domain & email setup

- **Domain:** Cloudflare Registrar (~$10/yr, at-cost) → DNS in Cloudflare.
  `app.domain.com` → Pages; `api.domain.com` → VPS IP (proxied or DNS-only;
  Caddy terminates TLS either way — if proxied, set SSL mode Full-strict).
- **Platform email (password resets):** Resend free (3k/mo, 100/day, 1 domain).
  Verify the domain: SPF + DKIM records, add DMARC. Set
  `RESEND_FROM_EMAIL=noreply@domain.com`, `APP_BASE_URL=https://app.domain.com`.
- **Per-company support mail:** each Company connects its **own** Gmail via App
  Password (their cost: $0). Document for customers: 2-Step Verification must be
  on to mint App Passwords; Gmail caps ~**500 sends/day per account** (a
  per-company ceiling, fine at this stage); Google is steering away from App
  Passwords long-term → the OAuth connector (ADR-0002's planned successor) is
  the roadmap item, not a launch blocker.

## 12. Expected free-tier limitations

| Service | Limit | When it bites |
|---|---|---|
| Neon free | 191.9 CU-hrs/mo, 0.5 GB | Worker keeps DB awake → ~186 CU-hrs at 0.25 CU; **near-zero headroom**. Storage caps KB size. Upgrade $19 early. |
| Groq free | strict req/day + TPM caps | A few hundred drafts/day; then PAYG (~$0.0012/draft). |
| Resend free | 100 emails/**day** | Password-reset bursts; signup waves. Pro $20 at ~100+ companies. |
| Sentry free | 5k events/mo, 1 user | A crash-loop eats the quota in hours; set rate limits in SDK. |
| Upstash free | 10k commands/day | Only if auth traffic spikes (or someone hammers login → rate limiting itself throttles them). |
| Oracle free | capacity + reclamation | Instance may be reclaimed; not for paying customers. |
| CF Pages free | 500 builds/mo | Non-issue. |
| Hetzner (paid, not free) | single node | The VPS **is** the availability story: a reboot = minutes of downtime. Acceptable for pilot; add a second node + LB later. |

Also a code-reality limit, not a tier limit: **sequential mailbox polling**.
~1–3 s per mailbox per cycle means freshness degrades past ~50–100 connected
mailboxes (minutes per sweep) — worker sharding/parallel polling is the
engineering item for the 100→1000 jump.

## 13. Exact deployment sequence

1. Register domain at Cloudflare; DNS zone live.
2. Create **Neon prod project** (separate from dev), pg16; create DDL role +
   runtime role; note pooler URL.
3. Provision **Hetzner CX32**; harden (SSH keys only, ufw allow 80/443/22,
   fail2ban, unattended-upgrades); install Docker + compose plugin.
4. Write prod env file on the server (chmod 600): `SECRET_KEY` (new),
   `DATABASE_URL` (Neon pooler, runtime role), `MAILBOX_ENCRYPTION_KEY` (new —
   **back up offline first**), `MAILBOX_ENCRYPTION_REQUIRED=true`,
   `ENVIRONMENT=production`, `COOKIE_SECURE=true`,
   `RATELIMIT_STORAGE_URI=redis://redis:6379/0`,
   `CORS_ORIGINS=https://app.domain.com`, `APP_BASE_URL=https://app.domain.com`,
   `GROQ_API_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, worker pool vars.
5. Add the small prod compose overlay (drop `db`, add Caddy with
   `api.domain.com`) — *the one implementation task in this plan* — plus Sentry
   SDK init and the worker heartbeat ping (B-3).
6. `docker compose up migrate` against Neon (DDL role) → must exit 0.
7. `docker compose up -d api worker redis caddy`; point `api.domain.com` DNS at
   the VPS; confirm `https://api.domain.com/health/ready` → 200.
8. Cloudflare Pages: connect the GitHub repo, root `frontend/`, build
   `npm ci && npm run build`, output `dist/`,
   `VITE_API_BASE_URL=https://api.domain.com`; map `app.domain.com`.
9. Verify the cookie flow cross-subdomain: login at `app.domain.com` → httpOnly
   `Secure` cookie set by api.domain.com → refresh + logout work.
10. Resend: verify domain (SPF/DKIM/DMARC); send a real password-reset.
11. Wire monitoring: Sentry DSN in env (both processes), UptimeRobot on
    `/health` + `/health/ready`, Healthchecks.io heartbeat from the worker.
12. Run the **staging checklist** (`runbooks/staging-deployment.md` §verify) on
    this stack, including the real inbound→draft→approve→send roundtrip on a
    dedicated mailbox (closes B-4).
13. Rollback rehearsal: redeploy the previous image tag; confirm Neon PITR is on.
14. Onboard the pilot company (pilot checklist in `LAUNCH_READINESS.md` flow).

## 14. Estimated monthly cost

Assumptions: ~20 inbound emails/company/day, ~$0.0012 Groq cost per draft,
VPS-based stack. Ranges are honest, not precise.

| Scale | Compute | DB (Neon) | LLM (Groq) | Email/Redis/Monitoring | **Total** |
|---|---|---|---|---|---|
| **10 companies** (~6k drafts/mo) | CX32 $8 | free $0 (tight) – $19 | $0–8 (free tier may cover) | $0 | **~$8–35/mo** |
| **100 companies** (~60k drafts/mo) | CX32–CX42 $8–17 | Launch $19 | $40–80 | Resend Pro maybe $20; rest $0 | **~$70–140/mo** |
| **1000 companies** (~600k drafts/mo) | 2–3 nodes or managed $40–150 | Scale $69–150 (storage!) | $400–750 | Resend $20, Upstash ~$10, Sentry Team $26 | **~$550–1,100/mo** |

The 1000-company column also carries **engineering prerequisites**, not just
bills: parallel/sharded mailbox polling, multiple workers (the
`FOR UPDATE SKIP LOCKED` queue already supports them), the OAuth mailbox
connector, image slimming, and probably managed/autoscaled compute. Revenue
context: at even $50/company/mo, 1000 companies = $50k MRR — infrastructure is
~2% of revenue; don't over-optimize it now.

---

## What I would choose launching today

**Cloudflare (domain + DNS + Pages) · Hetzner CX32 with the existing
docker-compose (Caddy + api + worker + redis) · Neon free→Launch · Groq PAYG ·
Resend free · Sentry + UptimeRobot + Healthchecks.io free.**
**≈ $9/mo + ~$10/yr domain + LLM usage.**

Why not pure-free: Oracle's Always Free is the only free compute that fits, and
its reclamation risk is wrong for a product holding companies' mailbox
credentials. $9/mo buys you out of that risk entirely. Why not a PaaS: every
managed option is 3–6× the price *because* the ML stack inflates RAM, and the
compose file the repo already ships makes the VPS path nearly as low-ops. The
runbooks' Cloud Run target stays the right scale-up path — adopt it after image
slimming, when autoscaling actually matters.

## Blockers to clear before production deployment

In order:

1. **Prod compose overlay + Caddy/TLS** — the one infra implementation task
   (small, uses existing compose).
2. **B-3 monitoring code**: Sentry SDK init (api + worker) + worker heartbeat
   ping. Small, but launching blind is not an option.
3. **B-5 send idempotency/retry** — duplicate/lost replies to real customers is
   the worst failure mode the app currently allows. Fix before pilot, or
   formally accept the risk for the pilot only.
4. **B-4 real inbound→draft→send roundtrip** on a dedicated mailbox (step 12).
5. **B-6 KB upload size/count caps** — before opening uploads to strangers.
6. **B-7 frontend cut-over decision** — pilot on the SPA; do not deploy
   Streamlit publicly.
7. Operational gates: `MAILBOX_ENCRYPTION_KEY` offline backup verified, Neon
   PITR on, rollback rehearsed, secrets distinct from dev.
8. *(Recommended, not blocking)* CPU-only-torch image slimming — cuts the image
   ~5 GB → ~1.5 GB, faster deploys, lower RAM, and unlocks Cloud Run later.
