"""Mailbox encryption key: fail-fast + refuse-without-key (H3).

Covers the missing, invalid, and valid key scenarios for the crypto helpers and
the startup self-check, plus the /mailbox/connect route refusing (503) when no
usable key is configured.
"""

import pytest
from cryptography.fernet import Fernet

from backend import crypto
from backend.config import MissingSettingError
from tests.helpers import register_company


@pytest.fixture
def set_key(monkeypatch):
    """Set MAILBOX_ENCRYPTION_KEY for one test and reset the Fernet cache."""

    def _set(value):
        monkeypatch.setattr(crypto.settings, "MAILBOX_ENCRYPTION_KEY", value)
        crypto._fernet.cache_clear()

    crypto._fernet.cache_clear()
    yield _set
    crypto._fernet.cache_clear()


def test_missing_key(set_key):
    set_key(None)
    assert crypto.is_configured() is False
    with pytest.raises(MissingSettingError):
        crypto.require_configured()
    # Missing is tolerated at startup unless required...
    crypto.validate_at_startup(required=False)  # no raise
    with pytest.raises(MissingSettingError):
        crypto.validate_at_startup(required=True)


def test_invalid_key(set_key):
    set_key("this-is-not-a-valid-fernet-key")
    assert crypto.is_configured() is False
    with pytest.raises(MissingSettingError):
        crypto.require_configured()
    # An invalid key always fails fast, regardless of the required flag.
    with pytest.raises(MissingSettingError):
        crypto.validate_at_startup(required=False)
    with pytest.raises(MissingSettingError):
        crypto.validate_at_startup(required=True)


def test_valid_key_roundtrip(set_key):
    set_key(Fernet.generate_key().decode())
    assert crypto.is_configured() is True
    crypto.require_configured()  # no raise
    crypto.validate_at_startup(required=True)  # no raise
    token = crypto.encrypt("app-password")
    assert token != b"app-password"
    assert crypto.decrypt(token) == "app-password"


async def test_connect_route_refuses_without_key(client, set_key):
    """/mailbox/connect returns 503 (not 500, not a stored plaintext) when the
    server has no usable encryption key — checked before any network work."""
    set_key(None)
    owner = await register_company(client, "mbx@acme.com", "Acme")
    res = await client.post(
        "/api/v1/mailbox/connect",
        json={
            "email_address": "support@acme.com",
            "app_password": "abcd efgh ijkl mnop",
        },
        headers=owner["headers"],
    )
    assert res.status_code == 503
