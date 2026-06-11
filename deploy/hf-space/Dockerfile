# Hugging Face Space variant of the production image (deploy/hf-space/).
#
# Mirrors the root ./Dockerfile (same two-stage build, same venv, same
# .dockerignore) with three deployment-specific deltas — and NOTHING else:
#   1. uid 1000 user (the HF Spaces convention) instead of 10001
#   2. CMD runs start.sh (api + worker in one container; a free Space is a
#      single container) instead of uvicorn alone
#   3. HF_HOME points at a writable cache dir for the runtime download of the
#      BGE embedding model (the Space disk is ephemeral; the model re-downloads
#      after a restart — acceptable, the hub is local to HF infra)
#
# Used by pushing the `hf-space` branch (where this file sits at the repo root
# as `Dockerfile`) to the Space remote — see README.md in this folder.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface

# HF Spaces convention: non-root user with uid 1000.
RUN useradd --create-home --uid 1000 user

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/.cache/huggingface /app/data \
    && chown -R user:user /app
USER user

EXPOSE 8000

CMD ["bash", "start.sh"]
