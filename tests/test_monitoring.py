"""Phase 7: Monitoring tests."""

from __future__ import annotations

import asyncio
import time

import pytest

from shakti import Shakti
from shakti.monitoring import Monitor, HealthStatus
from shakti.monitoring.health import CheckResult, HealthChecker
from shakti.monitoring.metrics import MetricsCollector
from shakti.testing import TestClient


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------

def test_metrics_record():
    m = MetricsCollector()
    m.record("GET", "/health", 200, 12.5)
    m.record("POST", "/users", 201, 45.0)
    m.record("GET", "/missing", 404, 5.0)
    m.record("GET", "/crash", 500, 8.0)

    s = m.summary()
    assert s["total_requests"] == 4
    assert s["error_count"] == 1
    assert s["error_rate_pct"] == 25.0
    assert s["response_time_ms"]["avg"] > 0


def test_metrics_endpoints():
    m = MetricsCollector()
    m.record("GET", "/posts", 200, 10.0)
    m.record("GET", "/posts", 200, 20.0)
    m.record("POST", "/posts", 201, 50.0)

    eps = m.endpoints()
    assert len(eps) >= 2
    get_posts = next(e for e in eps if e["path"] == "/posts" and e["method"] == "GET")
    assert get_posts["count"] == 2
    assert get_posts["avg_ms"] == 15.0


def test_metrics_uptime():
    m = MetricsCollector()
    time.sleep(0.05)
    assert m.uptime_seconds >= 0.04


def test_metrics_recent_requests():
    m = MetricsCollector()
    m.record("GET", "/a", 200, 1.0)
    m.record("GET", "/b", 200, 2.0)
    recent = m.recent_requests(5)
    assert len(recent) == 2
    assert recent[0]["path"] == "/b"  # most recent first


def test_metrics_active_tracking():
    m = MetricsCollector()
    m.start_request()
    m.start_request()
    assert m.summary()["active_requests"] == 2
    m.end_request()
    assert m.summary()["active_requests"] == 1


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

def test_health_check_pass():
    hc = HealthChecker()
    hc.add("ping", lambda: "pong")
    result = asyncio.run(hc.run("ping"))
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "pong"


def test_health_check_fail():
    hc = HealthChecker()
    hc.add("broken", lambda: 1 / 0)
    result = asyncio.run(hc.run("broken"))
    assert result.status == HealthStatus.UNHEALTHY
    assert "division by zero" in result.message or "ZeroDivisionError" in result.message


def test_health_check_async():
    hc = HealthChecker()

    async def async_check() -> str:
        await asyncio.sleep(0.01)
        return "async ok"

    hc.add("async", async_check)
    result = asyncio.run(hc.run("async"))
    assert result.status == HealthStatus.HEALTHY


def test_health_check_custom_result():
    hc = HealthChecker()

    def check() -> CheckResult:
        return CheckResult(name="custom", status=HealthStatus.DEGRADED, message="slow but alive")

    hc.add("custom", check)
    result = asyncio.run(hc.run("custom"))
    assert result.status == HealthStatus.DEGRADED


def test_health_check_overall_status():
    hc = HealthChecker()
    hc.add("ok", lambda: "fine")
    hc.add("bad", lambda: (_ for _ in ()).throw(Exception("down")))
    status = asyncio.run(hc.overall_status())
    assert status == HealthStatus.UNHEALTHY


def test_health_check_missing():
    hc = HealthChecker()
    result = asyncio.run(hc.run("nonexistent"))
    assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Monitor HTTP route tests
# ---------------------------------------------------------------------------

def _make_app() -> tuple[Shakti, Monitor]:
    app = Shakti()
    monitor = Monitor(title="Test Monitor")
    monitor.init_app(app)
    return app, monitor


def test_health_simple():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/monitor/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_live():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/monitor/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


def test_health_ready():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/monitor/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "checks" in data


def test_health_full():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/monitor/health/full")
    assert r.status_code == 200
    data = r.json()
    assert "metrics" in data
    assert "system" in data
    assert "checks" in data


def test_metrics_json():
    app, _ = _make_app()
    client = TestClient(app)
    client.get("/health")  # generate a request
    r = client.get("/monitor/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "metrics" in data
    assert data["metrics"]["total_requests"] >= 1


def test_endpoint_metrics():
    app, _ = _make_app()
    client = TestClient(app)
    client.get("/monitor/health")
    client.get("/monitor/health")
    r = client.get("/monitor/metrics/endpoints")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_recent_requests_route():
    app, _ = _make_app()
    client = TestClient(app)
    client.get("/monitor/health")
    r = client.get("/monitor/metrics/requests")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_dashboard_html():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/monitor/")
    assert r.status_code == 200
    assert b"Test Monitor" in r.content
    assert b"Dashboard" in r.content or b"Monitor" in r.content


def test_custom_health_check():
    app, monitor = _make_app()

    @monitor.health_check("database")
    async def check_db() -> str:
        return "connected"

    client = TestClient(app)
    r = client.get("/monitor/health/ready")
    checks = r.json()["checks"]
    names = [c["name"] for c in checks]
    assert "database" in names


def test_dashboard_escapes_health_check_message():
    """Regression: a failing health check's exception message (str(e),
    which can embed data the check itself pulled from elsewhere — a URL,
    a response body) must not render as live HTML/script on the
    dashboard, which by default has no auth in front of it."""
    app, monitor = _make_app()

    @monitor.health_check("bad")
    async def check_bad() -> str:
        raise RuntimeError("<script>alert(1)</script>")

    client = TestClient(app)
    r = client.get("/monitor/")
    assert r.status_code == 200
    assert b"<script>alert(1)</script>" not in r.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in r.content


def test_endpoint_metrics_group_by_route_template_not_raw_path():
    """Regression: per-endpoint stats must key on the route's path template
    (e.g. "/items/{id:int}"), not the raw request path — otherwise every
    unique id creates its own permanent, never-evicted dict entry."""
    app, monitor = _make_app()

    @app.get("/items/{id:int}")
    async def get_item(id: int) -> dict:
        return {"id": id}

    client = TestClient(app)
    for item_id in range(1, 51):
        client.get(f"/items/{item_id}")

    endpoints = monitor.metrics.endpoints(limit=100)
    matching = [e for e in endpoints if e["method"] == "GET" and "items" in e["path"]]
    assert len(matching) == 1
    assert matching[0]["path"] == "/items/{id:int}"
    assert matching[0]["count"] == 50


def test_recent_requests_show_literal_path_while_endpoints_stay_grouped():
    """Regression: endpoint aggregation groups by route template, but the
    recent-requests log must still show the literal path that was hit —
    these are two different views over the same request, not one."""
    app, monitor = _make_app()

    @app.get("/items/{id:int}")
    async def get_item(id: int) -> dict:
        return {"id": id}

    client = TestClient(app)
    client.get("/items/1")
    client.get("/items/2")

    recent = monitor.metrics.recent_requests(10)
    paths = {r["path"] for r in recent if r["path"].startswith("/items/")}
    assert paths == {"/items/1", "/items/2"}

    endpoints = monitor.metrics.endpoints(limit=100)
    matching = [e for e in endpoints if "items" in e["path"]]
    assert len(matching) == 1
    assert matching[0]["path"] == "/items/{id:int}"
    assert matching[0]["count"] == 2


def test_unmatched_requests_bucket_into_single_entry():
    """404s must not each create their own permanent per-path entry."""
    app, monitor = _make_app()
    client = TestClient(app)
    for path in ("/nope1", "/nope2", "/nope3"):
        client.get(path)

    endpoints = monitor.metrics.endpoints(limit=100)
    unmatched = [e for e in endpoints if e["path"] == "<unmatched>"]
    assert len(unmatched) == 1
    assert unmatched[0]["count"] == 3
    assert not any(e["path"] in ("/nope1", "/nope2", "/nope3") for e in endpoints)


def test_metrics_middleware_tracks_requests():
    app, monitor = _make_app()

    @app.get("/api/test")
    async def test_route() -> dict:
        return {"ok": True}

    client = TestClient(app)
    client.get("/api/test")
    client.get("/api/test")
    client.get("/api/test")

    assert monitor.metrics.summary()["total_requests"] >= 3
