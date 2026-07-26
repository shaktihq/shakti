"""Health check system."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            **({"metadata": self.metadata} if self.metadata else {}),
        }


class HealthChecker:
    def __init__(self) -> None:
        self._checks: dict[str, Callable] = {}

    def add(self, name: str, func: Callable) -> None:
        self._checks[name] = func

    def check(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._checks[name] = func
            return func
        return decorator

    async def run(self, name: str) -> CheckResult:
        func = self._checks.get(name)
        if not func:
            return CheckResult(name=name, status=HealthStatus.UNHEALTHY, message="Check not found")
        start = time.perf_counter()
        try:
            result = func()
            if asyncio.iscoroutine(result):
                result = await result
            elapsed = (time.perf_counter() - start) * 1000
            if isinstance(result, CheckResult):
                result.duration_ms = elapsed
                return result
            return CheckResult(name=name, status=HealthStatus.HEALTHY,
                               message=str(result) if result else "OK", duration_ms=elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return CheckResult(name=name, status=HealthStatus.UNHEALTHY,
                               message=str(e), duration_ms=elapsed)

    async def run_all(self) -> list[CheckResult]:
        tasks = [self.run(name) for name in self._checks]
        return await asyncio.gather(*tasks)

    async def overall_status(self) -> HealthStatus:
        results = await self.run_all()
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        if any(r.status == HealthStatus.DEGRADED for r in results):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
