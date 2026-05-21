"""Refresh-token lifecycle: issue, validate, rotate, revoke.

Refresh tokens are opaque random strings; only their SHA-256 hash is stored, so
a database leak does not expose usable tokens. Times are naive UTC for safe
comparisons on SQLite.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.refresh_token import RefreshToken


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_refresh_token(
    db: Session,
    user_id: int,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> str:
    """Create a refresh-token row; return the raw token (shown to the client once)."""
    raw = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash(raw),
            expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    db.commit()
    return raw


def get_active_refresh_token(db: Session, raw: str) -> RefreshToken | None:
    """Return the row if the token exists and is neither revoked nor expired."""
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _hash(raw))
        .first()
    )
    if row is None or row.revoked_at is not None:
        return None

    expires_at = row.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        if expires_at < _utcnow():
            return None
    return row


def revoke_refresh_token(db: Session, row: RefreshToken) -> None:
    """Mark a refresh token revoked."""
    row.revoked_at = _utcnow()
    db.commit()
