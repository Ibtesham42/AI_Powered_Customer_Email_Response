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


class Settings:
    """Process-wide backend settings."""

    # --- JWT / auth ---
    SECRET_KEY: str = _require("SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
