"""SSRF guard for URL knowledge-base ingestion (H4)."""

import pytest

from app.rag.url_guard import UnsafeUrlError, validate_public_url
from tests.helpers import register_company


@pytest.mark.parametrize(
    "url",
    [
        "http://8.8.8.8/",  # public IPv4 literal
        "https://93.184.216.34/page",  # public IPv4 literal (example.org)
    ],
)
def test_public_urls_allowed(url):
    validate_public_url(url)  # must not raise


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",  # loopback
        "http://localhost/",  # resolves to loopback
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
        "http://10.0.0.5/",  # private
        "http://192.168.1.1/admin",  # private
        "http://172.16.0.9/",  # private
        "http://[::1]/",  # IPv6 loopback
        "http://0.0.0.0/",  # unspecified
    ],
)
def test_internal_targets_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://127.0.0.1/",
        "//no-scheme.example.com",
    ],
)
def test_non_http_schemes_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url)


def test_missing_host_rejected():
    with pytest.raises(UnsafeUrlError):
        validate_public_url("http://")


async def test_url_ingest_route_rejects_internal(client):
    """POST /data/url rejects an internal/metadata target up front (400)."""
    owner = await register_company(client, "kb@acme.com", "Acme")
    res = await client.post(
        "/api/v1/data/url",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
        headers=owner["headers"],
    )
    assert res.status_code == 400
