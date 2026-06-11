# Zero-Budget Pilot Deployment ($0/month, no credit card)

_Living plan. History: the Oracle Always Free plan died on the no-credit-card
constraint; the Hugging Face Spaces plan died on the mail-egress probe
(**2026-06-11: `deploy/hf-probe` returned FAIL — imap:993 / smtp:465 / smtp:587
all "Network unreachable" from a Space**). HF Spaces cannot host a product that
speaks IMAP/SMTP. The `deploy/hf-space/` files are retained in case HF egress
policy ever changes._

## The surviving option

With $0, no card, **and** required outbound IMAP/SMTP, every container PaaS is
out (card-required, 512 MB ceilings, or mail-port filtering). What remains:

**Run the stack on your own always-on PC and publish the API through a free
tunnel.** This machine already runs the entire pipeline natively — the live
end-to-end test (mailbox connect, ingestion, RAG, Groq draft, real SMTP send)
executed on it — so mail egress, RAM, and even GPU embeddings are proven, not
hoped for.

### Two tunnel choices

| | **Tailscale Funnel** (default) | Cloudflare Tunnel |
|---|---|---|
| Cost / card | $0, no card (SSO signup) | $0, no card — **but needs a domain in your CF account** (~$10/yr; Porkbun accepts PayPal) |
| Hostname | stable `https://<machine>.<tailnet>.ts.net` | your own `api.<domain>` (nicer, custom) |
| TLS | automatic (Tailscale-issued cert) | automatic |
| Limits | HTTPS only on port 443; fair-use throughput (fine for JSON + 10 MB KB uploads) | effectively none for this scale |
| Cookie posture | cross-site with the SPA → `COOKIE_SAMESITE=none` | same-site possible if SPA is `app.<domain>` → keep `lax` |

Start with **Funnel** (strictly $0, zero purchases). If you can spend ~$10/yr
via PayPal on a domain later, switch to Cloudflare Tunnel for nicer URLs and
`SameSite=lax` — a config change, not a redeploy.

## 1. Architecture

```
 browser ─▶ Cloudflare Pages (SPA)                                       $0
               │  COOKIE_SAMESITE=none + CORS (cross-site with ts.net)
               ▼
 https://<machine>.<tailnet>.ts.net  (Tailscale Funnel, TLS)             $0
               ▼
 YOUR PC (Windows, the existing venv — no Docker needed)
   uvicorn backend.main:app  (api, :8000)        ──▶ Neon Postgres        $0
   python scripts/email_worker.py (worker)       ──▶ Upstash Redis (TLS)  $0
   POLL_INTERVAL_SECONDS=600                     ──▶ Groq free · Resend   $0
 Monitoring: Sentry · Healthchecks.io · UptimeRobot                      $0
```

- **State stays off the PC** (Neon + Upstash), same principle as every prior
  plan — a crash/reinstall loses nothing but uptime.
- Architecture unchanged: same two processes, same code, same env contract.
  Docker isn't required (and isn't installed on this PC); the venv path is the
  one already validated end-to-end.
- Redis: **Upstash free** (no card) satisfies the production
  `RATELIMIT_STORAGE_URI` fail-fast.

## 2. Setup sequence (Windows)

1. **Upstash**: free Redis DB → copy the `rediss://` URL.
2. **Tailscale**: install on the PC, sign in (Google/GitHub SSO, no card).
   Enable HTTPS certificates + Funnel for the tailnet (Admin console → DNS →
   HTTPS, and approve the Funnel node attribute when prompted), then:
   ```powershell
   tailscale funnel --bg 8000
   tailscale funnel status   # shows https://<machine>.<tailnet>.ts.net
   ```
3. **Production env**: copy `.env` to `.env.pilot` and set the production
   values — fresh `SECRET_KEY`, fresh `MAILBOX_ENCRYPTION_KEY` (backed up
   offline), `ENVIRONMENT=production`, `COOKIE_SECURE=true`,
   `COOKIE_SAMESITE=none`, `CORS_ORIGINS=https://<project>.pages.dev`,
   `APP_BASE_URL=https://<project>.pages.dev`, `POLL_INTERVAL_SECONDS=600`,
   `RATELIMIT_STORAGE_URI=rediss://…upstash…`, `SENTRY_DSN`,
   `WORKER_HEARTBEAT_URL`, Neon pooler `DATABASE_URL`, `GROQ_API_KEY`,
   `RESEND_API_KEY`. Load it for both processes.
4. **Run the two processes** (validated commands, from the repo root):
   ```powershell
   venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   venv\Scripts\python.exe scripts\email_worker.py
   ```
   Funnel forwards only to localhost — the api is never exposed directly.
5. **Keep the PC serving**: disable sleep/hibernate (`powercfg /change
   standby-timeout-ac 0`), set Windows Update active hours, and register both
   processes with **Task Scheduler** (run at startup, restart on failure) so a
   reboot self-heals.
6. **Frontend**: Cloudflare Pages, `VITE_API_BASE_URL=https://<machine>.<tailnet>.ts.net`.
7. **Monitoring**: UptimeRobot on `…ts.net/health` + `/health/ready`;
   Healthchecks.io heartbeat (also alerts when the PC is off); Sentry test
   event.
8. **Verify** (staging checklist): cross-site cookie login round-trips,
   rate-limit 429 via Upstash, KB upload→indexed, real inbound→draft→approve→
   send on a dedicated pilot mailbox (closes B-4).

## 3. Honest limitations

- **Your PC's uptime is the SLA.** Power cut, reboot, Windows Update, or
  closing the lid = pilot down. Healthchecks.io tells you within ~15 min.
  Set the pilot company's expectations accordingly (it's a pilot).
- Residential upload bandwidth bounds responsiveness (JSON API — fine).
- The `ts.net` URL looks technical; acceptable for one friendly pilot user,
  not for marketing. The domain+CF-Tunnel upgrade fixes optics for ~$10/yr.
- Don't run dev experiments on the same DB while the pilot is live — the
  pilot uses its own Neon project/branch and its own `.env.pilot`.
- Electricity ≈ a few $/month of household cost — no provider invoices.

## 4. Rejected alternatives (kept for the record)

- **GitHub Actions as the worker** ("scheduled cron worker"): ❌. Actions
  can't host the always-on API at all; scheduled crons have 5-min minimum +
  unreliable (often 15–60 min) timing; each run cold-pulls the multi-GB ML
  stack, so ~48 runs/day ≈ 10,000+ runner-minutes/month (the private-repo free
  tier is 2,000); and using Actions as a production compute platform —
  polling customers' mailboxes with stored credentials through CI runners —
  is against GitHub's Acceptable Use terms. Not salvageable.
- **Render free (no card)**: 512 MB OOMs on torch; background workers are
  paid-only; mail egress unverified anyway.
- **Modal/serverless-Python free credits**: torch cold-starts measured in
  minutes per invocation, always-on worker burns past the credit, off-label.
- **Kaggle/Colab as servers**: ToS violation, ephemeral, no.

## 5. Upgrade path

Unchanged in spirit: when ~$9/mo exists → Hetzner + `docker-compose.prod.yml`
(`docs/DEPLOYMENT_STRATEGY.md`), flip `VITE_API_BASE_URL` + cookie/CORS env,
re-point monitors. Nothing migrates (state is in Neon/Upstash). The interim
$10/yr domain step (CF Tunnel) already moves the URLs to `api.<domain>`, making
the eventual Hetzner switch invisible to the pilot user.
