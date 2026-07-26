"""Interval-based job scheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from shakti.workflows.models import ScheduledJob

logger = logging.getLogger("shakti.workflows.scheduler")


class Scheduler:
    """Run async functions on a fixed interval."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def add(
        self,
        func: Callable,
        *,
        name: str | None = None,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
        **kwargs: Any,
    ) -> ScheduledJob:
        total = seconds + minutes * 60 + hours * 3600 + days * 86400
        if total <= 0:
            raise ValueError("Interval must be > 0. Use seconds/minutes/hours/days.")
        job = ScheduledJob(
            name=name or func.__name__,
            func=func,
            interval_seconds=total,
            kwargs=kwargs,
        )
        self._jobs[job.name] = job
        logger.info("Scheduled %s every %.0fs", job.name, total)
        return job

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for job in self._jobs.values():
            task = asyncio.create_task(self._loop(job), name=f"scheduler-{job.name}")
            self._tasks.append(task)
        logger.info("Scheduler started (%d jobs)", len(self._jobs))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _loop(self, job: ScheduledJob) -> None:
        while self._running:
            await asyncio.sleep(job.interval_seconds)
            if not job.enabled:
                continue
            try:
                result = job.func(**job.kwargs)
                if asyncio.iscoroutine(result):
                    await result
                job.last_run = datetime.now(timezone.utc)
                job.run_count += 1
                logger.info("Scheduled job %s ran (total: %d)", job.name, job.run_count)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Scheduled job %s failed: %s", job.name, e)

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": j.name,
                "interval_seconds": j.interval_seconds,
                "last_run": j.last_run.isoformat() if j.last_run else None,
                "run_count": j.run_count,
                "enabled": j.enabled,
            }
            for j in self._jobs.values()
        ]
