"""Refresh-token cookie helpers (audit H1).

The refresh token rides in an httpOnly cookie so the browser keeps it out of
JavaScript's reach (no localStorage = no XSS exfiltration). The access token
stays in the JSON body (the SPA holds it in memory only). Cookie attributes
come from ``settings`` so a same-origin dev deploy and a separate-origin HTTPS
production deploy can both be served from one config.
"""

from fastapi import Request, Response

from backend.config import settings


def set_refresh_cookie(response: Response, token: str) -> None:
    """Attach the refresh token as an httpOnly cookie scoped to the auth path."""
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=settings.REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Expire the refresh cookie. Attributes must match those used to set it."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def read_refresh_token(request: Request, body_token: str | None) -> str | None:
    """Resolve the refresh token, cookie first then request body.

    Browser clients (the SPA) send only the cookie; non-browser clients (the
    legacy Streamlit dashboard, tests, future mobile) still pass it in the body.
    """
    return request.cookies.get(settings.REFRESH_COOKIE_NAME) or body_token
