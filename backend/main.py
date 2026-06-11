from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from backend import crypto
from backend.config import settings
from backend.database import engine
from backend.logging_config import configure_logging, get_logger
from backend.rate_limit import limiter
from backend.routes import (
    auth,
    dashboard,
    data,
    mailbox,
    messages,
    protected,
    tickets,
)
from backend.services.state_machine import InvalidTransitionError

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# Fail fast on a broken mailbox-encryption setup: an invalid key always aborts
# startup; a missing key aborts only when MAILBOX_ENCRYPTION_REQUIRED is set.
crypto.validate_at_startup(required=settings.MAILBOX_ENCRYPTION_REQUIRED)

app = FastAPI(
    title="AI Customer Support SaaS",
    version="1.0.0",
)

# CORS for the Vite + React SPA (ADR-0004). Dev uses the Vite proxy (same
# origin); these origins matter for a separate-origin production deploy.
# Credentials are enabled so the httpOnly refresh cookie (audit H1) is sent on a
# separate-origin deploy — which requires explicit origins, never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline security response headers (audit H1).

    Conservative on purpose so Swagger UI at /docs keeps working (no global
    Content-Security-Policy that would block its inline scripts). HSTS is only
    sent in production, where the app is served over HTTPS.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains",
        )
    return response


# Rate limiting (slowapi).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(InvalidTransitionError)
def _invalid_transition_handler(request: Request, exc: InvalidTransitionError):
    """Map an illegal state-machine transition to HTTP 409 Conflict."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# The database schema is managed entirely by Alembic — run `alembic upgrade head`.
# All feature routes are versioned under /api/v1.
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_v1.include_router(protected.router, prefix="/user", tags=["User"])
api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_v1.include_router(data.router, prefix="/data", tags=["Data"])
api_v1.include_router(mailbox.router, prefix="/mailbox", tags=["Mailbox"])
api_v1.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
api_v1.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(api_v1)

logger.info("AI Customer Support SaaS started")


# Unversioned infrastructure endpoints.
@app.get("/")
def read_root():
    return {"message": "SaaS Backend Running"}


@app.get("/health")
def health_check():
    """Liveness probe: the process is up. Deliberately does no DB work so an
    orchestrator never restarts a healthy app just because the DB blipped."""
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check():
    """Readiness probe: the app can serve traffic (the DB is reachable).

    A short-lived, engine-level connection — not the per-request get_db
    generator — keeps the check cheap and independent of request handling. Only
    ``SELECT 1``: migrations are a deploy-time gate, not a runtime condition.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database not ready") from exc
    return {"status": "ready"}
