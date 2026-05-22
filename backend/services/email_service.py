"""Transactional email via Resend.

Used for *platform* email — password resets and similar — which is distinct
from the per-Company support mailboxes. ``RESEND_API_KEY`` is read lazily so
the app starts without it; sending fails loudly if it is missing.
"""

import resend

from backend.config import MissingSettingError, settings
from backend.logging_config import get_logger

logger = get_logger(__name__)


def _reset_email_html(reset_url: str, expire_minutes: int) -> str:
    return (
        "<p>We received a request to reset your password.</p>"
        f'<p><a href="{reset_url}">Reset your password</a></p>'
        f"<p>This link expires in {expire_minutes} minutes. If you did not "
        "request it, you can safely ignore this email.</p>"
    )


def send_password_reset_email(to_email: str, reset_url: str) -> None:
    """Send a password-reset email via Resend.

    Raises ``MissingSettingError`` if the API key is unset, or a
    ``resend`` error if the provider rejects the send.
    """
    if not settings.RESEND_API_KEY:
        raise MissingSettingError(
            "RESEND_API_KEY is not set — required to send transactional email."
        )
    resend.api_key = settings.RESEND_API_KEY

    expire = settings.RESET_TOKEN_EXPIRE_MINUTES
    resend.Emails.send(
        {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your password",
            "html": _reset_email_html(reset_url, expire),
            "text": (
                f"Reset your password: {reset_url}\n\n"
                f"This link expires in {expire} minutes. If you did not "
                "request it, ignore this email."
            ),
        }
    )
    logger.info("Password-reset email sent to %s", to_email)
