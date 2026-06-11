"""Error monitoring (Sentry) — optional, fail-soft.

Both processes (the FastAPI api and the background worker) call
:func:`init_monitoring` once at startup. It is a no-op unless ``SENTRY_DSN`` is
configured, and a *guarded* import: a missing/broken ``sentry-sdk`` logs a
warning instead of taking the process down — monitoring must never be the
reason the app won't start.
"""

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger(__name__)


def init_monitoring(process: str) -> bool:
    """Initialise Sentry for this process. Returns True when active.

    ``process`` tags events as coming from the api or the worker, so one
    project cleanly separates the two.
    """
    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed — "
            "error monitoring is OFF. `pip install -r requirements.txt`."
        )
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        # Errors only — no performance tracing; keeps the free-tier event
        # budget for what matters and adds no per-request overhead.
        traces_sample_rate=0.0,
        # PII (emails, message bodies) stays out of the error tracker.
        send_default_pii=False,
    )
    sentry_sdk.set_tag("process", process)
    logger.info(
        "Sentry initialised (process=%s, env=%s)", process, settings.ENVIRONMENT
    )
    return True
