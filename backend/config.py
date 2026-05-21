"""Backend configuration.

Reads settings from the environment (loaded from ``.env``) and fails fast at
import time if a required secret is missing — see ``.env.example``.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Raw optional env value, resolved into Settings below.
_INGEST_COMPANY_ID = os.getenv("INGEST_COMPANY_ID")


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


class Settings:
    """Process-wide backend settings."""

    # --- JWT / auth ---
    SECRET_KEY: str = _require("SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    # Access token is kept long enough for the legacy Streamlit dashboard,
    # which has no silent refresh. Lower to ~15-30 min once the Next.js
    # frontend (with token refresh) ships.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    )

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Email ingestion (interim — per-company mailboxes arrive in Phase 3) ---
    # The Company that inbound email from the single global mailbox belongs to.
    INGEST_COMPANY_ID: int | None = (
        int(_INGEST_COMPANY_ID) if _INGEST_COMPANY_ID else None
    )


settings = Settings()
