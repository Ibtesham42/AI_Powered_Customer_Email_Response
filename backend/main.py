from fastapi import FastAPI

from backend.config import settings
from backend.database import Base, engine
from backend.logging_config import configure_logging, get_logger

# Import models so they register with Base.metadata before create_all().
from backend.models.company import Company  # noqa: F401
from backend.models.email import Email  # noqa: F401
from backend.models.refresh_token import RefreshToken  # noqa: F401
from backend.models.user import User  # noqa: F401
from backend.routes import auth, dashboard, data, email, protected

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

app = FastAPI(
    title="AI Customer Support SaaS",
    version="1.0.0",
)

# NOTE: create_all() is retired in Phase 1 in favour of Alembic migrations.
Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(protected.router, prefix="/user", tags=["User"])
app.include_router(email.router, prefix="/email", tags=["Email"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(data.router, prefix="/data", tags=["Data"])

logger.info("AI Customer Support SaaS started")


# Root route
@app.get("/")
def read_root():
    return {"message": "SaaS Backend Running"}


# Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}
