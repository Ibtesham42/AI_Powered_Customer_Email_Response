# Zero-Budget Pilot Deployment ($0/month)

_Plan for a validation/pilot launch with no hosting spend. Supersedes the
Hetzner recommendation in `docs/DEPLOYMENT_STRATEGY.md` **only while budget is
$0** — the Hetzner path remains the target once ~$9/mo is acceptable, and §5
makes that switch a 30-minute, zero-data-migration move._

## 1. Architecture (all free tiers)

```
 browser ─▶ Cloudflare Pages (SPA)                                $0
               │  app domain (see "domain" note)
               ▼
 Oracle Cloud Always Free — VM.Standard.A1.Flex (ARM)             $0
 4 OCPU · 24 GB RAM · Ubuntu 24.04 aarch64 · 200 GB storage
 ┌──────────────────────────────────────────────┐
 │ docker-compose.prod.yml (built ON the box):  │
 │  caddy (TLS, 80/443) → api (uvicorn)         │──▶ Neon Postgres
 │  worker (IMAP poll + AI queue)               │    + pgvector    $0
 │  redis (rate limiting)                       │──▶ Groq free tier $0
 └──────────────────────────────────────────────┘──▶ Resend free   $0
 Monitoring: Sentry free · UptimeRobot free · Healthchecks.io free $0
```

Design principle: **all state lives OFF the free VM.** The database is Neon,
certificates re-issue automatically, the image rebuilds from git. If Oracle
reclaims the instance (the #1 risk), nothing is lost — re-provision and go.

Why this exact split:
- **Oracle A1.Flex** is the only free compute that clears the app's ~2 GB/process
  RAM floor (torch + BGE in both api and worker). 24 GB is 3× more than the
  paid Hetzner pick.
- **Neon stays** (free tier) rather than self-hosting Postgres on the VM:
  durability must not depend on a reclaimable freebie.
- **Redis on-box** via the existing compose service: rate-limit counters are
  disposable state.
- The repo's `docker-compose.prod.yml` + `Caddyfile` are reused as-is.

### Prerequisite tweaks (small, config-level — do before deploying)
1. ✅ **Worker poll interval is env-tunable** (`POLL_INTERVAL_SECONDS`, default
   10). On the free tier set **`POLL_INTERVAL_SECONDS=600`** in the server's
   `.env` — see the Neon math in §4.
2. **Domain decision** (affects cookies):
   - *Recommended (~$10/yr, not monthly):* one domain on Cloudflare —
     `app.domain.com` (Pages) + `api.domain.com` (VM). Same-site → the existing
     `SameSite=lax` refresh cookie works unchanged.
   - *Strictly $0:* SPA on `<project>.pages.dev`, API on a free DuckDNS
     subdomain. These are **cross-site**, so set `COOKIE_SAMESITE=none` (+
     `COOKIE_SECURE=true`, already required) and put the pages.dev origin in
     `CORS_ORIGINS`. Supported by the existing config; slightly weaker CSRF
     posture and looks less credible to pilot users.

## 2. Step-by-step setup

1. **Oracle account.** Sign up for Oracle Cloud Free Tier (card required for
   identity; not charged). Pick a **home region with A1 capacity** (less
   popular regions fare better — capacity errors at instance-create are common;
   retry or script retries).
   *Strongly recommended:* upgrade the account to **Pay-As-You-Go** while using
   only Always-Free shapes — still $0, but removes the idle-reclamation policy
   and improves capacity access. Set a **budget alert at $1** as a tripwire.
2. **Create the VM.** Shape `VM.Standard.A1.Flex`, 4 OCPU / 24 GB, Ubuntu 24.04
   (aarch64), 100 GB boot volume (within the free 200 GB), SSH key auth.
3. **Open the network.** In the VCN security list: allow TCP 80 + 443 ingress.
   **Oracle gotcha:** the Ubuntu images also ship host iptables REJECT rules —
   `sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT` (and 443), then persist
   (`netfilter-persistent save`). Both layers must allow traffic.
4. **Harden + Docker.** ufw allow 22/80/443; fail2ban; unattended-upgrades;
   install Docker Engine + compose plugin (arm64 packages are standard).
5. **DNS.** Point `api.domain.com` (or the DuckDNS name) at the VM's public IP.
6. **Secrets.** `git clone` the repo; create `.env` (chmod 600) per the
   checklist at the top of `docker-compose.prod.yml`, including `API_DOMAIN`,
   `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `SENTRY_DSN`,
   `WORKER_HEARTBEAT_URL`, `POLL_INTERVAL_SECONDS=600`, and the Neon URL.
   Back up `MAILBOX_ENCRYPTION_KEY` offline first.
7. **Build & start (native arm64 build, ~15–30 min first time):**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   curl https://api.domain.com/health/ready   # expect {"status":"ready"}
   ```
   The aarch64 torch wheel is CPU-only by nature — the ARM image is actually
   *slimmer* than the amd64 one. **Known risk:** legacy-path deps
   (`bitsandbytes`, `tf-keras`, `faiss-cpu`) may lack aarch64 wheels for the
   resolved versions; they are used only by the standalone Streamlit apps, not
   the backend — if the build fails on one, removing/conditioning that legacy
   dep is the fix (small, justified change).
8. **Frontend.** Cloudflare Pages → connect the GitHub repo, root `frontend/`,
   build `npm ci && npm run build`, output `dist/`,
   `VITE_API_BASE_URL=https://api.domain.com`.
9. **Monitoring accounts** (all free): Sentry project → `SENTRY_DSN`;
   Healthchecks.io check → `WORKER_HEARTBEAT_URL`; UptimeRobot monitors on
   `/health` + `/health/ready`. Restart compose after env changes.
10. **Verify** with the staging checklist (`runbooks/staging-deployment.md`):
    cookie login flow, rate-limit 429, KB upload→indexed, and the **real
    inbound→draft→approve→send roundtrip** on a dedicated pilot mailbox (B-4).

## 3. Tradeoffs vs. the Hetzner plan (~$9/mo)

| | Oracle Always Free | Hetzner CX32 |
|---|---|---|
| Cost | $0 | ~$8/mo |
| RAM/CPU | 24 GB / 4 ARM OCPU (better!) | 8 GB / 4 vCPU x86 |
| **Reliability** | **Reclamation risk** (mitigated by PAYG upgrade, not eliminated); capacity lottery at creation; weaker support | Boringly reliable; predictable |
| Architecture | **arm64** — native build on the box; legacy-dep wheel risk; CI's amd64 image not directly reusable | amd64 — matches CI exactly |
| Ops posture | Same compose file, same runbook | Same |
| Suitability | Validation + first pilot users | First paying customers |

The deciding question: *can you tolerate the VM disappearing with a few hours
of downtime while you re-provision?* For unpaid pilot validation — yes (state
is in Neon; recovery is steps 2–7, ~1 hour). For paying customers — no; that's
what the $9 buys.

## 4. Expected limits at $0

| Resource | Free limit | Practical ceiling |
|---|---|---|
| **Neon compute** | 191.9 CU-hrs/mo | At 10 s polling the DB never suspends → ~186 CU-hrs idle-burn (over budget with api traffic). At **10-min polling** the DB sleeps between polls → roughly 75–110 CU-hrs, leaving real headroom. Email pickup latency becomes ≤ ~10 min — fine for human-reviewed support. |
| **Neon storage** | 0.5 GB | ~100 MB of KB text (chunks ≈ 3 KB/vector + HNSW overhead) + tickets/messages. Keep `KB_MAX_DOCS_PER_COMPANY` at default; watch storage in the Neon console. |
| **Groq free tier** | order of ~1k requests/day (limits change; check console) | ≈ **500–1,000 drafts/day** ceiling → comfortable for **5–15 pilot companies** at ~20–50 emails/day each. Excess drafts simply wait in queue (worker retries next cycle). |
| **Companies** | — | **~5–15.** Sequential IMAP polling adds ~1–3 s per mailbox per cycle (irrelevant at 10-min cadence). |
| **Resend** | 100/day | Password resets only — ample. |
| **Sentry** | 5k events/mo | Fine unless something crash-loops; rate-limit in the project settings. |
| **Oracle** | 4 OCPU/24 GB, 200 GB, 10 TB egress/mo | Compute is the least constrained resource in the whole stack. |

## 5. Migration path to Hetzner (when budget exists)

Designed to be a DNS flip — **no data migrates** (state is in Neon; certs
re-issue; rate-limit counters are disposable):

1. Provision Hetzner CX32 (amd64), harden, install Docker (≈ §2 steps 4).
2. Copy `.env` to the new box (same values; same `API_DOMAIN`).
3. `git clone` + `docker compose -f docker-compose.prod.yml up -d --build`
   (or pull a CI-built amd64 image — CI already validates that architecture).
4. Lower the `api.domain.com` DNS TTL in advance (300 s), then switch the A
   record to the Hetzner IP. Caddy obtains a fresh certificate on first hit.
5. Watch `/health/ready` + Sentry on the new box; stop the Oracle compose stack
   once traffic has moved. Keep the Oracle VM as a free warm spare, or delete.
6. Nothing changes for Pages, Neon, Groq, Resend, or the monitoring accounts.

Total switchover effort ≈ 30–60 minutes, downtime ≈ DNS TTL.
