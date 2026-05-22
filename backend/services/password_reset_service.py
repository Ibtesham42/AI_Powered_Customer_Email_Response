"""Password-reset token lifecycle: issue, validate, consume.

Reset tokens are opaque random strings; only their SHA-256 hash is stored, so
a database leak does not expose usable tokens. Tokens are single-use and
short-lived (``RESET_TOKEN_EXPIRE_MINUTES``). Times are naive UTC for safe
comparisons, matching ``auth_service``.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.password_reset_token import PasswordResetToken


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_reset_token(db: Session, user_id: int) -> str:
    """Create a reset-token row; return the raw token (shown to the user once,
    in the reset email)."""
    raw = secrets.token_urlsafe(48)
    db.add(
        PasswordResetToken(
            user_id=user_id,
            token_hash=_hash(raw),
            expires_at=_utcnow()
            + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
        )
    )
    db.commit()
    return raw


def get_valid_reset_token(db: Session, raw: str) -> PasswordResetToken | None:
    """Return the row if the token exists and is neither used nor expired."""
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash(raw))
        .first()
    )
    if row is None or row.used_at is not None:
        return None

    expires_at = row.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        if expires_at < _utcnow():
            return None
    return row


def consume_reset_token(db: Session, row: PasswordResetToken) -> None:
    """Mark a reset token used so it cannot be replayed."""
    row.used_at = _utcnow()
    db.commit()
