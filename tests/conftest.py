"""Shared test fixtures.

The suite runs against an in-memory SQLite database so it needs no external
services. The pgvector-backed ``kb_chunks`` table uses a Postgres-only column
type, so it is excluded from the test schema; tests that need real vector
retrieval are skipped unless a pgvector database is provided (see the RAG
tests). Routes are driven over HTTP with ``httpx.ASGITransport`` — the classic
``TestClient`` is incompatible with httpx 0.28.
"""

import os

# Must be set before importing backend.config (it fails fast on a missing key).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.rate_limit import limiter  # noqa: E402

# slowapi's limiter is process-global and in-memory; across many tests the
# per-minute signup/login limits would trip (429). Disable it for tests — rate
# limiting itself is exercised separately, not in these flow tests.
limiter.enabled = False

# One shared in-memory database for the whole process (StaticPool keeps the
# single underlying connection alive so the schema and data persist).
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

# Exclude Postgres-only tables from the SQLite test schema:
#  - kb_chunks      uses the pgvector Vector type
#  - audit_logs     uses JSONB
# Audit writes are best-effort (audit_service swallows failures), so flows still
# succeed without the table. Vector retrieval + audit assertions belong in the
# Postgres-backed CI run (Phase 7 chunk 6).
_POSTGRES_ONLY = {"kb_chunks", "audit_logs"}
_TEST_TABLES = [t for t in Base.metadata.sorted_tables if t.name not in _POSTGRES_ONLY]


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _schema():
    """Fresh schema per test for isolation."""
    Base.metadata.create_all(_engine, tables=_TEST_TABLES)
    yield
    Base.metadata.drop_all(_engine, tables=_TEST_TABLES)


@pytest.fixture
def db():
    """A session against the test database, for seeding domain rows directly."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
