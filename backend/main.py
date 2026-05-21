from fastapi import APIRouter, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.database import Base, engine
from backend.logging_config import configure_logging, get_logger

# Import models so they register with Base.metadata before create_all().
from backend.models.company import Company  # noqa: F401
from backend.models.email import Email  # noqa: F401
from backend.models.refresh_token import RefreshToken  # noqa: F401
from backend.models.user import User  # noqa: F401
from backend.rate_limit import limiter
from backend.routes import auth, dashboard, data, email, protected

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

app = FastAPI(
    title="AI Customer Support SaaS",
    version="1.0.0",
)

# Rate limiting (slowapi).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# NOTE: create_all() is retired in Phase 1 (chunk 4) in favour of Alembic.
Base.metadata.create_all(bind=engine)

# All feature routes are versioned under /api/v1.
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_v1.include_router(protected.router, prefix="/user", tags=["User"])
api_v1.include_router(email.router, prefix="/email", tags=["Email"])
api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_v1.include_router(data.router, prefix="/data", tags=["Data"])
app.include_router(api_v1)

logger.info("AI Customer Support SaaS started")


# Unversioned infrastructure endpoints.
@app.get("/")
def read_root():
    return {"message": "SaaS Backend Running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
