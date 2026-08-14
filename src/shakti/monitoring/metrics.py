"""Request metrics collector."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class RequestRecord:
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class MetricsCollector:
    """Collects and aggregates request metrics in memory."""

    def __init__(self, max_requests: int = 1000) -> None:
        self._start_time = time.monotonic()
        self._started_at = datetime.now(UTC)
        self._requests: deque[RequestRecord] = deque(maxlen=max_requests)
        self._total = 0
        self._errors = 0
        self._active = 0
        self._by_endpoint: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "count": 0, "errors": 0, "total_ms": 0.0, "min_ms": float("inf"), "max_ms": 0.0
        })
        self._by_status: dict[int, int] = defaultdict(int)

    def record(
        self,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        *,
        endpoint: str | None = None,
    ) -> None:
        """Record one request.

        ``path`` is the literal request path, shown as-is in
        ``recent_requests()``. ``endpoint`` (defaults to ``path``) is what
        per-endpoint stats are grouped by — pass the matched route's
        template (e.g. ``/posts/{id:int}``) so the group count stays
        bounded by route count instead of growing per unique id.
        """
        rec = RequestRecord(method=method, path=path, status_code=status, duration_ms=duration_ms)
        self._requests.appendleft(rec)
        self._total += 1
        self._by_status[status] += 1

        if status >= 500:
            self._errors += 1

        key = f"{method} {endpoint if endpoint is not None else path}"
        ep = self._by_endpoint[key]
        ep["count"] += 1
        ep["total_ms"] += duration_ms
        ep["min_ms"] = min(ep["min_ms"], duration_ms)
        ep["max_ms"] = max(ep["max_ms"], duration_ms)
        if status >= 400:
            ep["errors"] += 1

    def start_request(self) -> None:
        self._active += 1

    def end_request(self) -> None:
        self._active = max(0, self._active - 1)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def summary(self) -> dict[str, Any]:
        recent = list(self._requests)
        durations = [r.duration_ms for r in recent]
        avg_ms = sum(durations) / len(durations) if durations else 0
        sorted_d = sorted(durations)
        p95 = sorted_d[int(len(sorted_d) * 0.95)] if sorted_d else 0
        p99 = sorted_d[int(len(sorted_d) * 0.99)] if sorted_d else 0
        error_rate = (self._errors / self._total * 100) if self._total else 0
        uptime = self.uptime_seconds
        return {
            "uptime_seconds": round(uptime, 1),
            "uptime_human": _human_duration(uptime),
            "started_at": self._started_at.isoformat(),
            "total_requests": self._total,
            "active_requests": self._active,
            "error_count": self._errors,
            "error_rate_pct": round(error_rate, 2),
            "response_time_ms": {
                "avg": round(avg_ms, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "min": round(min(durations), 2) if durations else 0,
                "max": round(max(durations), 2) if durations else 0,
            },
            "status_codes": dict(sorted(self._by_status.items())),
        }

    def endpoints(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = []
        for key, data in self._by_endpoint.items():
            method, _, path = key.partition(" ")
            avg = data["total_ms"] / data["count"] if data["count"] else 0
            rows.append({
                "method": method,
                "path": path,
                "count": data["count"],
                "errors": data["errors"],
                "avg_ms": round(avg, 2),
                "min_ms": round(data["min_ms"], 2) if data["min_ms"] != float("inf") else 0,
                "max_ms": round(data["max_ms"], 2),
            })
        return sorted(rows, key=lambda r: r["count"], reverse=True)[:limit]

    def recent_requests(self, n: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "method": r.method,
                "path": r.path,
                "status": r.status_code,
                "duration_ms": round(r.duration_ms, 2),
                "time": r.timestamp.strftime("%H:%M:%S"),
            }
            for r in list(self._requests)[:n]
        ]


def _human_duration(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s//60}m {s%60}s"
    if s < 86400:
        return f"{s//3600}h {(s%3600)//60}m"
    return f"{s//86400}d {(s%86400)//3600}h"
