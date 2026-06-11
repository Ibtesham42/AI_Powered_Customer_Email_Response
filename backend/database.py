import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env so DATABASE_URL is available regardless of import order — Alembic
# imports this module directly without going through backend.config.
load_dotenv()

# Database URL from the environment; defaults to local SQLite for development.
# For Postgres (Neon, Supabase, Cloud SQL) set DATABASE_URL in .env.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./saas.db")

# check_same_thread is a SQLite-only connect argument.
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Connection pool is env-tunable, but only for a real DB (Postgres). SQLite uses
# StaticPool/SingletonThreadPool, which reject pool_size/max_overflow — and the
# test suite runs on in-memory SQLite, so those paths must stay untouched. This
# module is imported by Alembic directly, so it reads os.getenv here rather than
# importing backend.config (avoids circular/ordering issues). The worker
# container caps its pool low (DB_POOL_SIZE/DB_MAX_OVERFLOW); the API uses
# defaults. pool_recycle drops connections before a cloud provider idle-kills
# them.
_pg = not DATABASE_URL.startswith("sqlite")
_pool_kwargs = (
    dict(
        pool_pre_ping=True,  # drop stale connections (important for cloud Postgres)
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    )
    if _pg
    else {"pool_pre_ping": True}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    **_pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


# FastAPI dependency: yields a database session per request.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
