from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.logging_config import configure_logging, get_logger
from backend.rate_limit import limiter
from backend.routes import (
    auth,
    dashboard,
    data,
    messages,
    protected,
    tickets,
)
from backend.services.state_machine import InvalidTransitionError

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

app = FastAPI(
    title="AI Customer Support SaaS",
    version="1.0.0",
)

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
    return {"status": "ok"}
