"""限流与部署前检查测试。"""

from __future__ import annotations

import pytest


def test_memory_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from app.services import rate_limit

    rate_limit._redis_checked = True
    rate_limit._redis_client = None
    rate_limit._buckets.clear()
    key = "test:memory"
    assert rate_limit.check_rate_limit(key, limit=2, window_seconds=60) is True
    assert rate_limit.check_rate_limit(key, limit=2, window_seconds=60) is True
    assert rate_limit.check_rate_limit(key, limit=2, window_seconds=60) is False
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")


def test_rate_limit_bypassed_in_pytest():
    from app.services.rate_limit import check_rate_limit

    assert check_rate_limit("pytest:key", limit=1, window_seconds=60) is True
    assert check_rate_limit("pytest:key", limit=1, window_seconds=60) is True


def test_preflight_ok_with_sqlite_memory(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SESSION_SECRET", "unit-test-secret-value")
    monkeypatch.delenv("APP_ENV", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()

    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "preflight.py"
    spec = importlib.util.spec_from_file_location("preflight", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.run_preflight() == 0
    get_settings.cache_clear()


def test_health_includes_version(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "version" in payload
    assert "disk_free_mb" in payload


def test_enforce_upload_rate_limit_raises_429(monkeypatch):
    from fastapi import HTTPException

    from app.api import request_limits
    from app.services import rate_limit

    monkeypatch.setattr(request_limits.os, "getenv", lambda key, default=None: default)
    rate_limit._redis_checked = True
    rate_limit._redis_client = None
    rate_limit._buckets.clear()

    calls = {"count": 0}

    def fake_check(key, limit, window_seconds):
        calls["count"] += 1
        return calls["count"] <= 1

    monkeypatch.setattr(request_limits, "check_rate_limit", fake_check)
    request = type("Req", (), {"headers": {}, "client": type("C", (), {"host": "127.0.0.1"})()})()
    actor = type("Actor", (), {"is_guest": True, "user": type("U", (), {"id": 1})()})()

    request_limits.enforce_upload_rate_limit(request, actor)
    with pytest.raises(HTTPException) as exc:
        request_limits.enforce_upload_rate_limit(request, actor)
    assert exc.value.status_code == 429
