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

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,  # drop stale connections (important for cloud Postgres)
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
