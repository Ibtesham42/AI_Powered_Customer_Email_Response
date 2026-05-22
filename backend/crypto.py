"""Symmetric encryption for secrets stored at rest.

Mailbox App Passwords must never sit in the database as plaintext (ADR-0002).
This module wraps Fernet (AES-128-CBC + HMAC authentication) behind a tiny
``encrypt`` / ``decrypt`` pair.

The key is the ``MAILBOX_ENCRYPTION_KEY`` environment variable — a *critical*
secret: lose it and every stored mailbox credential becomes unrecoverable.
The key is read lazily, so the app still starts without it; only the first
encrypt/decrypt call fails, with a clear message.
"""

from functools import lru_cache

from cryptography.fernet import Fernet

from backend.config import MissingSettingError, settings

_KEY_HELP = (
    'Generate one with: python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Build the Fernet instance once from ``MAILBOX_ENCRYPTION_KEY``."""
    key = settings.MAILBOX_ENCRYPTION_KEY
    if not key:
        raise MissingSettingError(
            f"MAILBOX_ENCRYPTION_KEY is not set — required to store or read "
            f"mailbox credentials. {_KEY_HELP}"
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise MissingSettingError(
            f"MAILBOX_ENCRYPTION_KEY is not a valid Fernet key. {_KEY_HELP}"
        ) from exc


def encrypt(plaintext: str) -> bytes:
    """Encrypt a secret for storage. Returns the Fernet token as bytes."""
    return _fernet().encrypt(plaintext.encode())


def decrypt(token: bytes) -> str:
    """Decrypt a stored secret.

    Raises ``cryptography.fernet.InvalidToken`` if the key is wrong or the
    stored data is corrupt — callers should treat that as an unusable mailbox.
    """
    return _fernet().decrypt(bytes(token)).decode()
