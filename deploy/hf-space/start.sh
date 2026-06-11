#!/usr/bin/env bash
# Hugging Face Space entrypoint: run the api and the worker as two separate
# processes in ONE container (a free Space is a single container; the
# "worker never runs inside the API process" rule is intact — these are
# distinct OS processes sharing nothing but the image).
set -u

# Worker in a restart loop: scripts/email_worker.py already self-heals inside
# its own loop, but if the *process* ever exits (unhandled OOM kill, etc.) we
# bring it back rather than running api-only. Healthchecks.io (the worker
# heartbeat) still alerts if it stays down.
(
  while true; do
    python scripts/email_worker.py
    echo "worker exited (code $?) — restarting in 5s" >&2
    sleep 5
  done
) &

# The api is PID 1's foreground child: if uvicorn dies the container exits and
# the Space restarts everything. Container stop kills the worker mid-cycle —
# safe by design (queue claims roll back; the send path lives in the api).
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
