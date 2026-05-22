"""Security-relevant event logging.

Writes one ``AuditLog`` row per security-relevant action — signup, login,
logout, message send, draft reject. Routes call :func:`record` once; all the
detail of building and persisting the row lives here.

An audit write must never break the action it records. :func:`record`
therefore catches every exception, logs it loudly, and returns — a failed
audit insert degrades observability, not the request. Because of this, always
call :func:`record` *after* the action's own ``commit`` has succeeded, so a
rollback here can only discard the (failed) audit row.
"""

from fastapi import Request
from sqlalchemy.orm import Session

from backend.logging_config import get_logger
from backend.models.audit_log import AuditLog

logger = get_logger(__name__)


def _client_ip(request: Request | None) -> str | None:
    """Best-effort client IP from a request, or ``None`` if unavailable."""
    if request is None or request.client is None:
        return None
    return request.client.host


def record(
    db: Session,
    *,
    action: str,
    request: Request | None = None,
    company_id: int | None = None,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Write one ``AuditLog`` row. Never raises.

    ``action`` is a short stable verb (e.g. ``"login"``, ``"message_sent"``).
    ``entity_type``/``entity_id`` point at the affected domain row;
    ``metadata`` carries free-form context. The client IP is taken from
    ``request`` when given.
    """
    try:
        db.add(
            AuditLog(
                action=action,
                company_id=company_id,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                ip_address=_client_ip(request),
                meta=metadata,
            )
        )
        db.commit()
    except Exception:
        # Observability loss only — must not surface to the caller.
        logger.exception("Failed to write audit log for action %r", action)
        db.rollback()
