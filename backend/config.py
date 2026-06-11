"""Backend configuration.

Reads settings from the environment (loaded from ``.env``) and fails fast at
import time if a required secret is missing — see ``.env.example``.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class MissingSettingError(RuntimeError):
    """Raised when a required environment variable is not set."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingSettingError(
            f"Required environment variable {name!r} is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Process-wide backend settings."""

    # --- Environment ---
    # "production" tightens defaults: refresh-cookie Secure flag on, HSTS header
    # emitted (audit H1). Anything else (default) is treated as development.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    # --- JWT / auth ---
    SECRET_KEY: str = _require("SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    # Short-lived: the React SPA refreshes transparently on 401, and short
    # access tokens limit the window of a stolen token (audit H2; revocation is
    # via token_version). The legacy Streamlit dashboard now re-logs-in when it
    # expires — acceptable while it is being retired.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # --- Refresh-token cookie (audit H1) ---
    # The SPA holds the access token in memory and never sees the refresh token:
    # it rides in an httpOnly cookie the browser can't expose to JS (closes the
    # localStorage XSS-exfiltration vector). Scoped to the auth path so it is
    # only sent to /refresh and /logout, shrinking the CSRF surface; SameSite
    # plus bearer-token (non-cookie) APIs cover the rest.
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "acs_refresh_token")
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    # Secure defaults on in production (HTTPS-only); off in dev so the cookie
    # works over http://localhost. Override with COOKIE_SECURE if needed.
    COOKIE_SECURE: bool = (
        _is_truthy(os.getenv("COOKIE_SECURE"))
        if os.getenv("COOKIE_SECURE") is not None
        else os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
    )
    # "lax" suits a same-origin deploy (recommended). A separate-origin SPA must
    # set "none" (which requires Secure) and add its origin to CORS_ORIGINS.
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
    # Optional parent domain (e.g. ".example.com") for a separate-origin deploy.
    COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN") or None

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Rate limiting (slowapi) ---
    # Storage backend for request rate limits. Unset => in-memory (per-process),
    # which is wrong once more than one instance runs (each gets its own
    # counters). A multi-instance deploy (Cloud Run, multiple workers) must point
    # this at shared Redis. REDIS_URL is accepted as a convenient alias.
    RATELIMIT_STORAGE_URI: str | None = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv(
        "REDIS_URL"
    )

    # --- Mailbox credential encryption ---
    # Fernet key used to encrypt stored mailbox App Passwords (see ADR-0002).
    # Optional at startup so the app still runs without mailbox features; the
    # crypto helper fails loudly on first use if it is missing or invalid.
    MAILBOX_ENCRYPTION_KEY: str | None = os.getenv("MAILBOX_ENCRYPTION_KEY")
    # When true, the app refuses to start without a valid key (set this in any
    # deployment that uses Company mailboxes). When false (dev default), the app
    # still starts but mailbox features refuse until a key is configured. An
    # *invalid* key always fails fast at startup, regardless of this flag.
    MAILBOX_ENCRYPTION_REQUIRED: bool = os.getenv(
        "MAILBOX_ENCRYPTION_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}

    # --- Transactional email (Resend) ---
    # Platform email (password resets), distinct from per-Company support
    # mailboxes. Optional at startup; the email service fails loudly on first
    # use if the key is missing.
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    # --- Password reset ---
    # Base URL the reset link points at (the frontend reset page; Phase 7).
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))

    # --- CORS (frontend SPA) ---
    # Browser origins allowed to call the API. In dev the Vite proxy makes the
    # SPA same-origin so this is unused; set it for a separate-origin production
    # deploy (comma-separated). CORS runs with credentials enabled so the
    # refresh cookie (audit H1) flows on a separate-origin deploy — which means
    # origins must be listed explicitly here (the "*" wildcard is incompatible
    # with credentials).
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    # --- Escalation engine (Phase 5) ---
    # A fresh AI draft escalates its Ticket to a human when confidence falls
    # below this, or once the thread already has this many outbound replies
    # (the AI's answers aren't resolving it). Other rules — needs_human,
    # complaint intent, manual reject — are unconditional.
    ESCALATION_CONFIDENCE_THRESHOLD: int = int(
        os.getenv("ESCALATION_CONFIDENCE_THRESHOLD", "40")
    )
    ESCALATION_MAX_REPLIES: int = int(os.getenv("ESCALATION_MAX_REPLIES", "2"))


settings = Settings()
