---
title: mail-egress-probe
emoji: 📬
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Mail-egress probe

Tests whether this Hugging Face Space can open **outbound IMAP (993) and SMTP
(465)** connections to Gmail — the go/no-go gate for the zero-budget pilot
plan (`docs/runbooks/zero-budget-pilot.md` in the app repo). No credentials
are used or needed: a TLS handshake + server greeting proves the path.

## How to run

1. Create a new Space at huggingface.co → **New Space** → SDK: **Docker** →
   visibility: private is fine.
2. Upload the two files in this folder (`Dockerfile`, `probe.py`) plus this
   `README.md` to the Space (web upload or git push). The YAML header above is
   the required Space metadata — keep it.
3. The Space builds (~1 min) and starts. Open the Space page — the embedded
   app shows a JSON document. Refresh to re-run live.

## How to interpret

- `"verdict": "PASS"` → both 993 and 465 are reachable. The HF Space pilot
  plan is viable — proceed with `deploy/hf-space/`.
- `"verdict": "FAIL"` → check the per-target `error` fields:
  - `TimeoutError` / `ConnectionRefusedError` on 993/465 → the platform
    filters mail ports. **The plan is dead on HF** — use the fallback
    (own PC + Cloudflare Tunnel) from the runbook. (587 succeeding while 465
    fails is still a FAIL: the app uses implicit-TLS 465.)
  - `gaierror` (DNS) on everything → transient/platform DNS issue; rebuild or
    retry before concluding.

Delete the Space after the test.
