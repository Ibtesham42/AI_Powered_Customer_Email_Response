"""Shared rate limiter (slowapi).

Storage backend depends on configuration: when ``RATELIMIT_STORAGE_URI`` (or
``REDIS_URL``) is set, limits are tracked in Redis so they are shared across
instances — required for any multi-instance deploy (e.g. Cloud Run). When it is
unset, slowapi falls back to in-memory storage, which is fine only for a single
instance.

In **production** the in-memory fallback is a security regression: with several
instances each keeps its own counters, so the effective login/signup/forgot-
password limits multiply by the instance count and brute-force / enumeration
protection silently degrades. We therefore refuse to start in production without
a shared store, and warn loudly in dev (audit C2 security review H1).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import MissingSettingError, settings
from backend.logging_config import get_logger

logger = get_logger(__name__)

_kwargs: dict = {"key_func": get_remote_address}
if settings.RATELIMIT_STORAGE_URI:
    _kwargs["storage_uri"] = settings.RATELIMIT_STORAGE_URI
elif settings.is_production:
    raise MissingSettingError(
        "RATELIMIT_STORAGE_URI (or REDIS_URL) is required in production — "
        "refusing to run with per-process in-memory rate limiting, which does "
        "not hold across instances."
    )
else:
    logger.warning(
        "Rate limiting is using in-memory storage (per-process). Set "
        "RATELIMIT_STORAGE_URI / REDIS_URL for any multi-instance deploy."
    )

limiter = Limiter(**_kwargs)
