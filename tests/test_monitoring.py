"""Monitoring: Sentry init (optional, fail-soft) and the worker heartbeat."""

import sys
import types

from backend import monitoring
from backend.config import settings


def test_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.setattr(settings, "SENTRY_DSN", None)
    assert monitoring.init_monitoring(process="api") is False


def test_sentry_missing_sdk_is_fail_soft(monkeypatch):
    """DSN set but sentry-sdk not importable -> warn and continue, never raise."""
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://x@example.ingest.sentry.io/1")
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)  # forces ImportError
    assert monitoring.init_monitoring(process="api") is False


def test_sentry_initialises_when_available(monkeypatch):
    """With a DSN and an importable SDK, init is called with our settings."""
    calls = {}
    fake = types.ModuleType("sentry_sdk")
    fake.init = lambda **kw: calls.update(kw)
    fake.set_tag = lambda k, v: calls.update({f"tag:{k}": v})
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://x@example.ingest.sentry.io/1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    assert monitoring.init_monitoring(process="worker") is True
    assert calls["dsn"].startswith("https://x@")
    assert calls["environment"] == "production"
    assert calls["send_default_pii"] is False
    assert calls["traces_sample_rate"] == 0.0
    assert calls["tag:process"] == "worker"


def test_worker_poll_interval_comes_from_settings():
    """The cycle cadence is env-tunable (Neon free tier runs at 600s)."""
    import scripts.email_worker as worker

    assert worker.POLL_INTERVAL_SECONDS == settings.POLL_INTERVAL_SECONDS
    assert settings.POLL_INTERVAL_SECONDS == 10  # default preserved


def test_heartbeat_noop_without_url(monkeypatch):
    import scripts.email_worker as worker

    monkeypatch.setattr(settings, "WORKER_HEARTBEAT_URL", None)
    called = []
    monkeypatch.setattr(worker.httpx, "get", lambda *a, **k: called.append(a))
    worker._ping_heartbeat()
    assert called == []


def test_heartbeat_pings_url(monkeypatch):
    import scripts.email_worker as worker

    monkeypatch.setattr(settings, "WORKER_HEARTBEAT_URL", "https://hc.example/ping/1")
    called = []
    monkeypatch.setattr(worker.httpx, "get", lambda url, **k: called.append(url))
    worker._ping_heartbeat()
    assert called == ["https://hc.example/ping/1"]


def test_heartbeat_failure_is_swallowed(monkeypatch):
    """A dead monitoring service must never disturb the worker."""
    import scripts.email_worker as worker

    monkeypatch.setattr(settings, "WORKER_HEARTBEAT_URL", "https://hc.example/ping/1")

    def boom(url, **k):
        raise OSError("network down")

    monkeypatch.setattr(worker.httpx, "get", boom)
    worker._ping_heartbeat()  # must not raise
