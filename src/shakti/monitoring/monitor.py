"""Monitor — health checks, metrics, system info, and dashboard.

Usage::

    from shakti.monitoring import Monitor

    monitor = Monitor()
    monitor.init_app(app)

    # Custom health check
    @monitor.health_check("database")
    async def check_db() -> str:
        await db.engine.connect()
        return "connected"

    # Visit http://localhost:8000/monitor for the dashboard
"""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from shakti.http.request import Request
from shakti.http.response import HTMLResponse, JSONResponse, Response
from shakti.middleware.base import BaseHTTPMiddleware
from shakti.monitoring.health import HealthChecker, HealthStatus
from shakti.monitoring.metrics import MetricsCollector
from shakti.routing.router import Router

if TYPE_CHECKING:
    from shakti.application import Shakti


def _get_system_info() -> dict[str, Any]:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_pct": round(cpu, 1),
            "memory_pct": round(mem.percent, 1),
            "memory_used_mb": round(mem.used / 1024 / 1024, 1),
            "memory_total_mb": round(mem.total / 1024 / 1024, 1),
            "disk_pct": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
        }
    except ImportError:
        return {
            "cpu_pct": 0, "memory_pct": 0,
            "memory_used_mb": 0, "memory_total_mb": 0,
            "disk_pct": 0, "disk_used_gb": 0, "disk_total_gb": 0,
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "note": "pip install psutil for system metrics",
        }


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track every request through the metrics collector."""

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        self._collector.start_request()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            # Endpoint aggregation groups by the matched route's template
            # (e.g. "/posts/{id:int}"), not the raw path — otherwise every
            # unique id (or every 404'd garbage path) creates its own
            # permanent, never-evicted entry. The recent-requests log still
            # shows the literal path that was actually hit.
            route = request.scope.get("route")
            endpoint_label = route.path if route is not None else "<unmatched>"
            self._collector.record(
                request.method, request.path,
                response.status_code, duration_ms,
                endpoint=endpoint_label,
            )
            return response
        finally:
            self._collector.end_request()


class Monitor:
    """Monitoring: metrics, health checks, system info, and dashboard."""

    def __init__(
        self,
        *,
        prefix: str = "/monitor",
        title: str = "Shakti Monitor",
        max_requests: int = 1000,
    ) -> None:
        self.prefix = prefix
        self.title = title
        self.metrics = MetricsCollector(max_requests=max_requests)
        self.health = HealthChecker()
        self._middleware = MetricsMiddleware(self.metrics)

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: Shakti) -> None:
        app.container.register_instance(Monitor, self)
        app.add_middleware(self._middleware)

        # Built-in health checks
        self.health.add("app", lambda: "running")

        app.include_router(self._build_router(), prefix=self.prefix)

    # ------------------------------------------------------------------
    # Health check decorator
    # ------------------------------------------------------------------
    def health_check(self, name: str) -> Callable:
        """Register a custom health check.

        Usage::

            @monitor.health_check("database")
            async def check_db() -> str:
                await db.engine.connect()
                return "connected"
        """
        def decorator(func: Callable) -> Callable:
            self.health.add(name, func)
            return func
        return decorator

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _mon = self

        @router.get("/health")
        async def health_simple() -> dict:
            """Basic health check — used by load balancers."""
            return {"status": "ok", "uptime": _mon.metrics.uptime_seconds}

        @router.get("/health/live")
        async def health_live() -> dict:
            """Kubernetes liveness probe."""
            return {"status": "alive"}

        @router.get("/health/ready")
        async def health_ready() -> Response:
            """Kubernetes readiness probe — runs all health checks."""
            results = await _mon.health.run_all()
            status = HealthStatus.HEALTHY
            for r in results:
                if r.status == HealthStatus.UNHEALTHY:
                    status = HealthStatus.UNHEALTHY
                    break
                if r.status == HealthStatus.DEGRADED:
                    status = HealthStatus.DEGRADED
            body = {
                "status": status.value,
                "checks": [r.to_dict() for r in results],
            }
            code = 200 if status == HealthStatus.HEALTHY else (207 if status == HealthStatus.DEGRADED else 503)
            return JSONResponse(body, status_code=code)

        @router.get("/health/full")
        async def health_full() -> dict:
            """Full health check with system info."""
            results = await _mon.health.run_all()
            overall = await _mon.health.overall_status()
            return {
                "status": overall.value,
                "checks": [r.to_dict() for r in results],
                "system": _get_system_info(),
                "metrics": _mon.metrics.summary(),
            }

        @router.get("/metrics")
        async def metrics_json() -> dict:
            """JSON metrics for Prometheus/Grafana scraping."""
            return {
                "metrics": _mon.metrics.summary(),
                "endpoints": _mon.metrics.endpoints(),
                "system": _get_system_info(),
            }

        @router.get("/metrics/endpoints")
        async def endpoint_metrics() -> list:
            return _mon.metrics.endpoints()

        @router.get("/metrics/requests")
        async def recent_requests() -> list:
            return _mon.metrics.recent_requests(50)

        @router.get("/")
        async def dashboard() -> HTMLResponse:
            """HTML monitoring dashboard — auto-refreshes every 10s."""
            from shakti.monitoring.dashboard import render_dashboard
            results = await _mon.health.run_all()
            overall = await _mon.health.overall_status()
            return HTMLResponse(render_dashboard(
                metrics=_mon.metrics.summary(),
                system=_get_system_info(),
                health=[r.to_dict() for r in results],
                endpoints=_mon.metrics.endpoints(),
                recent=_mon.metrics.recent_requests(30),
                overall_status=overall.value,
                title=_mon.title,
            ))

        return router

    def __repr__(self) -> str:
        return f"<Monitor prefix={self.prefix!r}>"
