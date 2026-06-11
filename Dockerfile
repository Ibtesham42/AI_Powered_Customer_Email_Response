# Single shared image for the api, worker, and migrate processes.
#
# The api (uvicorn) and worker (email_worker.py) share one Python codebase, so
# we build ONE image and differentiate by `command` in docker-compose / Cloud
# Run. This is the standard Cloud Run pattern and still satisfies the
# "api and worker are separate processes/containers" rule — same image, two
# deployments, each with its own entrypoint.
#
# NOTE: this image is large because of the ML stack (torch +
# sentence-transformers pull in multi-hundred-MB CPU/CUDA wheels). Slimming it
# down — installing the CPU-only torch wheel and dropping the legacy
# streamlit/faiss path — is a DEFERRED follow-up and explicitly NOT part of
# Phase 7 Chunk 6 (C2). Do not refactor dependencies here.

# ---------- Stage 1: builder ----------
# Build wheels in a throwaway stage so build-only artefacts (pip cache, compiler
# scratch) never reach the runtime image.
FROM python:3.12-slim AS builder

# Faster, quieter, deterministic pip; no .pyc clutter.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg2-binary ships manylinux wheels, so no libpq build deps are required.
# Copy ONLY requirements first so the (slow) pip layer is cached and reused
# whenever application source changes but dependencies do not.
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root runtime user — never run the app as root.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Bring the already-built virtualenv over from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Copy the application source (everything not excluded by .dockerignore). No
# secrets are baked in: config is read from the runtime environment / .env.
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command is the api; compose / Cloud Run override it per service
# (worker -> `python scripts/email_worker.py`, migrate -> `alembic upgrade head`).
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
