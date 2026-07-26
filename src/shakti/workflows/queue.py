"""Async job queue with worker pool and retry logic."""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from shakti.workflows.models import Job, JobStatus

logger = logging.getLogger("shakti.workflows")


class JobQueue:
    """Async job queue — runs jobs in the background with retries."""

    def __init__(self, workers: int = 4, max_history: int = 500) -> None:
        self._workers = workers
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: dict[str, Job] = {}
        self._history: deque[str] = deque(maxlen=max_history)
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for i in range(self._workers):
            task = asyncio.create_task(self._worker(i), name=f"shakti-worker-{i}")
            self._tasks.append(task)
        logger.info("JobQueue started with %d workers", self._workers)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("JobQueue stopped")

    async def enqueue(
        self,
        func: Callable,
        *,
        name: str | None = None,
        max_retries: int = 3,
        delay_seconds: float = 0,
        **kwargs: Any,
    ) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            name=name or func.__name__,
            func=func,
            kwargs=kwargs,
            max_retries=max_retries,
            scheduled_at=datetime.now(timezone.utc) if delay_seconds == 0 else None,
        )
        self._jobs[job.id] = job
        self._history.appendleft(job.id)

        if delay_seconds > 0:
            asyncio.create_task(self._delayed_enqueue(job, delay_seconds))
        else:
            await self._queue.put(job)

        logger.debug("Enqueued job %s (%s)", job.id[:8], job.name)
        return job

    async def _delayed_enqueue(self, job: Job, delay: float) -> None:
        await asyncio.sleep(delay)
        job.scheduled_at = datetime.now(timezone.utc)
        await self._queue.put(job)

    async def _worker(self, worker_id: int) -> None:
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._run_job(job)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker %d error: %s", worker_id, e)

    async def _run_job(self, job: Job) -> None:
        if job.status == JobStatus.CANCELLED:
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        logger.info("Running job %s (%s)", job.id[:8], job.name)

        try:
            result = job.func(**job.kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            job.result = result
            job.status = JobStatus.COMPLETED
            job.finished_at = datetime.now(timezone.utc)
            logger.info("Job %s completed in %dms", job.id[:8],
                       int((job.finished_at - job.started_at).total_seconds() * 1000))
        except Exception as e:
            job.error = f"{type(e).__name__}: {e}"
            job.retries += 1

            if job.retries <= job.max_retries:
                delay = 2 ** job.retries  # 2s, 4s, 8s
                job.status = JobStatus.RETRYING
                logger.warning("Job %s failed (attempt %d/%d), retrying in %ds: %s",
                               job.id[:8], job.retries, job.max_retries, delay, e)
                asyncio.create_task(self._delayed_enqueue(job, delay))
            else:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(timezone.utc)
                logger.error("Job %s failed permanently: %s\n%s",
                             job.id[:8], e, traceback.format_exc())

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            return True
        return False

    def list(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Job]:
        jobs = [self._jobs[jid] for jid in self._history if jid in self._jobs]
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        return jobs[:limit]

    def stats(self) -> dict[str, Any]:
        all_jobs = list(self._jobs.values())
        by_status: dict[str, int] = {}
        for j in all_jobs:
            by_status[j.status.value] = by_status.get(j.status.value, 0) + 1
        return {
            "total": len(all_jobs),
            "queue_size": self._queue.qsize(),
            "workers": self._workers,
            "by_status": by_status,
        }
