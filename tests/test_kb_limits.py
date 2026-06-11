"""Knowledge-base ingestion limits (pilot blocker B-6): file-size cap,
per-Company document quota, FAQ length caps."""

import pytest

from backend.config import settings
from backend.services import kb_service
from tests.helpers import register_company


@pytest.fixture(autouse=True)
def _stub_ingest(monkeypatch):
    """The in-process embed/index step is out of scope here (and needs the
    Postgres-only kb_chunks table) — stub the background task."""
    monkeypatch.setattr(kb_service, "ingest_document", lambda document_id: None)


async def test_upload_within_limits_accepted(client):
    owner = await register_company(client, "kb1@acme.com", "Acme")
    res = await client.post(
        "/api/v1/data/upload",
        files={"file": ("policy.txt", b"Refunds within 30 days.", "text/plain")},
        headers=owner["headers"],
    )
    assert res.status_code == 200
    assert res.json()["document"]["status"] == "pending"


async def test_oversized_upload_rejected_413(client, monkeypatch):
    owner = await register_company(client, "kb2@acme.com", "Acme")
    monkeypatch.setattr(settings, "KB_MAX_FILE_MB", 0)  # cap = 0 bytes

    res = await client.post(
        "/api/v1/data/upload",
        files={"file": ("big.txt", b"x" * 1024, "text/plain")},
        headers=owner["headers"],
    )
    assert res.status_code == 413
    # Nothing registered for the rejected file.
    docs = await client.get("/api/v1/data/documents", headers=owner["headers"])
    assert docs.json() == []


async def test_document_quota_enforced_on_upload(client, monkeypatch):
    owner = await register_company(client, "kb3@acme.com", "Acme")
    monkeypatch.setattr(settings, "KB_MAX_DOCS_PER_COMPANY", 1)

    first = await client.post(
        "/api/v1/data/upload",
        files={"file": ("a.txt", b"doc one", "text/plain")},
        headers=owner["headers"],
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/data/upload",
        files={"file": ("b.txt", b"doc two", "text/plain")},
        headers=owner["headers"],
    )
    assert second.status_code == 409


async def test_document_quota_enforced_on_faq(client, monkeypatch):
    owner = await register_company(client, "kb4@acme.com", "Acme")
    monkeypatch.setattr(settings, "KB_MAX_DOCS_PER_COMPANY", 0)

    res = await client.post(
        "/api/v1/data/faq",
        json={"question": "Refunds?", "answer": "30 days."},
        headers=owner["headers"],
    )
    assert res.status_code == 409


async def test_faq_length_caps(client):
    owner = await register_company(client, "kb5@acme.com", "Acme")
    res = await client.post(
        "/api/v1/data/faq",
        json={"question": "Refunds?", "answer": "x" * 5001},
        headers=owner["headers"],
    )
    assert res.status_code == 422
