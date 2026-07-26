"""WorkflowEngine — background jobs, retries, and scheduling for Shakti.

Usage::

    from shakti.workflows import WorkflowEngine

    workflows = WorkflowEngine()
    workflows.init_app(app)

    # Define a background job
    @workflows.job
    async def send_email(to: str, subject: str, body: str) -> str:
        # ... send email logic
        return f"Email sent to {to}"

    # Enqueue it from any route
    @app.post("/register")
    async def register(body: dict) -> dict:
        user = await create_user(body)
        await workflows.enqueue(send_email,
            to=user["email"],
            subject="Welcome!",
            body="Thanks for joining."
        )
        return {"user": user}

    # Schedule recurring jobs
    @workflows.every(minutes=30)
    async def cleanup_sessions():
        # runs every 30 minutes
        pass

    @workflows.every(hours=24)
    async def daily_report():
        pass
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from shakti.exceptions import HTTPException
from shakti.routing.router import Router
from shakti.workflows.models import Job, JobStatus
from shakti.workflows.queue import JobQueue
from shakti.workflows.scheduler import Scheduler

if TYPE_CHECKING:
    from shakti.application import Shakti

logger = logging.getLogger("shakti.workflows")


class WorkflowEngine:
    """Background job queue + scheduler for Shakti."""

    def __init__(
        self,
        *,
        workers: int = 4,
        max_retries: int = 3,
        max_history: int = 500,
        prefix: str = "/jobs",
    ) -> None:
        self.workers = workers
        self.default_max_retries = max_retries
        self.prefix = prefix
        self._queue = JobQueue(workers=workers, max_history=max_history)
        self._scheduler = Scheduler()
        self._registered: list[Callable] = []

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: "Shakti") -> None:
        app.container.register_instance(WorkflowEngine, self)
        app.include_router(self._build_router(), prefix=self.prefix)

        @app.on_startup
        async def _start_workflows() -> None:
            await self._queue.start()
            await self._scheduler.start()
            logger.info("WorkflowEngine started")

        @app.on_shutdown
        async def _stop_workflows() -> None:
            await self._queue.stop()
            await self._scheduler.stop()
            logger.info("WorkflowEngine stopped")

    # ------------------------------------------------------------------
    # Job decorator
    # ------------------------------------------------------------------
    def job(self, func: Callable) -> Callable:
        """Register a function as a background job.

        Usage::

            @workflows.job
            async def process_report(report_id: int) -> str:
                ...
                return "done"
        """
        self._registered.append(func)
        return func

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------
    async def enqueue(
        self,
        func: Callable,
        *,
        name: str | None = None,
        max_retries: int | None = None,
        delay_seconds: float = 0,
        **kwargs: Any,
    ) -> Job:
        """Add a job to the queue. Returns Job with id for status tracking."""
        return await self._queue.enqueue(
            func,
            name=name or func.__name__,
            max_retries=max_retries if max_retries is not None else self.default_max_retries,
            delay_seconds=delay_seconds,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Scheduler decorators
    # ------------------------------------------------------------------
    def every(
        self,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0,
        name: str | None = None,
    ) -> Callable:
        """Schedule a function to run at a fixed interval.

        Usage::

            @workflows.every(minutes=15)
            async def refresh_cache() -> None:
                pass

            @workflows.every(hours=1)
            async def hourly_report() -> None:
                pass
        """
        def decorator(func: Callable) -> Callable:
            self._scheduler.add(
                func,
                name=name or func.__name__,
                seconds=seconds,
                minutes=minutes,
                hours=hours,
                days=days,
            )
            return func
        return decorator

    # ------------------------------------------------------------------
    # Status / management
    # ------------------------------------------------------------------
    def status(self, job_id: str) -> Job:
        job = self._queue.get(job_id)
        if not job:
            raise HTTPException(404, f"Job {job_id!r} not found")
        return job

    def cancel(self, job_id: str) -> bool:
        return self._queue.cancel(job_id)

    def stats(self) -> dict[str, Any]:
        return {
            **self._queue.stats(),
            "scheduled_jobs": len(self._scheduler._jobs),
            "registered_jobs": len(self._registered),
        }

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _wf = self

        @router.get("/stats")
        async def stats() -> dict:
            return _wf.stats()

        @router.get("/scheduled")
        async def scheduled() -> list:
            return _wf._scheduler.list()

        @router.get("/")
        async def list_jobs() -> list:
            return [j.to_dict() for j in _wf._queue.list(limit=50)]

        @router.get("/{job_id}")
        async def get_job(job_id: str) -> dict:
            return _wf.status(job_id).to_dict()

        @router.delete("/{job_id}")
        async def cancel_job(job_id: str) -> dict:
            if not _wf.cancel(job_id):
                raise HTTPException(400, "Job cannot be cancelled (not in pending state)")
            return {"cancelled": job_id}

        @router.post("/{job_id}/retry")
        async def retry_job(job_id: str) -> dict:
            job = _wf.status(job_id)
            if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
                raise HTTPException(400, f"Can only retry failed/cancelled jobs. Status: {job.status.value}")
            job.status = JobStatus.PENDING
            job.error = None
            job.retries = 0
            await _wf._queue._queue.put(job)
            return {"retrying": job_id, "job": job.to_dict()}

        return router
