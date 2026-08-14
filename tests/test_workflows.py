"""Phase 6: Workflow Engine tests."""

from __future__ import annotations

import asyncio
import time

import pytest

from shakti import Shakti
from shakti.testing import TestClient
from shakti.workflows import WorkflowEngine, Job, JobStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(**kwargs) -> WorkflowEngine:
    return WorkflowEngine(workers=2, **kwargs)


# ---------------------------------------------------------------------------
# Job queue tests
# ---------------------------------------------------------------------------

def test_enqueue_and_status():
    wf = make_engine()

    async def _run():
        await wf._queue.start()
        results = []

        @wf.job
        async def add(a: int, b: int) -> int:
            results.append(a + b)
            return a + b

        job = await wf.enqueue(add, a=2, b=3)
        assert job.id
        assert job.status == JobStatus.PENDING

        await asyncio.sleep(0.3)
        await wf._queue.stop()
        return job, results

    job, results = asyncio.run(_run())
    assert job.status == JobStatus.COMPLETED
    assert job.result == 5
    assert results == [5]


def test_job_failure_and_retry():
    wf = WorkflowEngine(workers=1)
    call_count = {"n": 0}

    async def _run():
        await wf._queue.start()

        async def flaky() -> str:
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ValueError("Not yet!")
            return "ok"

        job = await wf.enqueue(flaky, max_retries=3)
        # Wait for retries (2s + 4s backoff)
        await asyncio.sleep(8)
        await wf._queue.stop()
        return job

    job = asyncio.run(_run())
    assert job.status == JobStatus.COMPLETED
    assert job.result == "ok"
    assert call_count["n"] == 3


def test_job_permanent_failure():
    wf = WorkflowEngine(workers=1)

    async def _run():
        await wf._queue.start()

        async def always_fail() -> None:
            raise RuntimeError("always")

        job = await wf.enqueue(always_fail, max_retries=1)
        await asyncio.sleep(5)
        await wf._queue.stop()
        return job

    job = asyncio.run(_run())
    assert job.status == JobStatus.FAILED
    assert "RuntimeError" in (job.error or "")


def test_cancel_pending_job():
    wf = WorkflowEngine(workers=0)  # No workers — job stays pending

    async def _run():
        await wf._queue.start()

        async def slow() -> None:
            await asyncio.sleep(10)

        job = await wf.enqueue(slow)
        cancelled = wf.cancel(job.id)
        await wf._queue.stop()
        return job, cancelled

    job, cancelled = asyncio.run(_run())
    assert cancelled is True
    assert job.status == JobStatus.CANCELLED


def test_delayed_job():
    wf = WorkflowEngine(workers=1)
    ran = {"at": None}

    async def _run():
        await wf._queue.start()
        start = time.monotonic()

        async def delayed_task() -> str:
            ran["at"] = time.monotonic()
            return "done"

        job = await wf.enqueue(delayed_task, delay_seconds=0.5)
        await asyncio.sleep(1.5)
        await wf._queue.stop()
        return job, start

    job, start = asyncio.run(_run())
    assert job.status == JobStatus.COMPLETED
    assert ran["at"] is not None
    assert ran["at"] - start >= 0.4  # ran after delay


def test_cancel_retrying_job():
    wf = WorkflowEngine(workers=1)

    async def _run():
        await wf._queue.start()

        async def always_fail() -> None:
            raise RuntimeError("nope")

        job = await wf.enqueue(always_fail, max_retries=5)
        # Let it fail once and enter its backoff (2s) as RETRYING.
        await asyncio.sleep(0.3)
        assert job.status == JobStatus.RETRYING
        cancelled = wf.cancel(job.id)
        # Wait past the backoff window to confirm it doesn't run again.
        await asyncio.sleep(2.5)
        await wf._queue.stop()
        return job, cancelled

    job, cancelled = asyncio.run(_run())
    assert cancelled is True
    assert job.status == JobStatus.CANCELLED


def test_stop_cancels_pending_retry_timers():
    wf = WorkflowEngine(workers=1)

    async def _run():
        await wf._queue.start()

        async def always_fail() -> None:
            raise RuntimeError("nope")

        await wf.enqueue(always_fail, max_retries=5)
        await asyncio.sleep(0.3)  # let it fail once, schedule a 2s retry timer
        assert len(wf._queue._delayed_tasks) == 1
        await wf._queue.stop()
        return wf._queue._delayed_tasks

    remaining = asyncio.run(_run())
    assert len(remaining) == 0


def test_job_list_and_filter():
    wf = WorkflowEngine(workers=1)

    async def _run():
        await wf._queue.start()

        async def quick() -> str:
            return "done"

        async def fail_job() -> None:
            raise ValueError("fail")

        j1 = await wf.enqueue(quick)
        j2 = await wf.enqueue(fail_job, max_retries=0)
        await asyncio.sleep(0.5)
        await wf._queue.stop()
        return j1, j2

    j1, j2 = asyncio.run(_run())
    all_jobs = wf._queue.list()
    assert len(all_jobs) >= 2
    completed = wf._queue.list(status="completed")
    assert all(j.status == JobStatus.COMPLETED for j in completed)


def test_stats():
    wf = make_engine()
    stats = wf.stats()
    assert "total" in stats
    assert "workers" in stats
    assert "by_status" in stats
    assert stats["workers"] == 2


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_scheduler_runs_job():
    wf = make_engine()
    runs = []

    @wf.every(seconds=0.2)
    async def tick() -> None:
        runs.append(1)

    async def _run():
        await wf._queue.start()
        await wf._scheduler.start()
        await asyncio.sleep(0.7)
        await wf._scheduler.stop()
        await wf._queue.stop()

    asyncio.run(_run())
    assert len(runs) >= 2


def test_scheduler_list():
    wf = make_engine()

    @wf.every(minutes=5, name="my_job")
    async def periodic() -> None:
        pass

    jobs = wf._scheduler.list()
    assert any(j["name"] == "my_job" for j in jobs)
    assert any(j["interval_seconds"] == 300 for j in jobs)


# ---------------------------------------------------------------------------
# HTTP route tests
# ---------------------------------------------------------------------------

def _make_app() -> tuple[Shakti, WorkflowEngine]:
    app = Shakti()
    wf = WorkflowEngine(workers=1)
    wf.init_app(app)
    return app, wf


def test_stats_route():
    app, wf = _make_app()
    with TestClient(app) as client:
        r = client.get("/jobs/stats")
        assert r.status_code == 200
        assert "workers" in r.json()


def test_list_jobs_route():
    app, wf = _make_app()
    with TestClient(app) as client:
        r = client.get("/jobs/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_get_job_route():
    app, wf = _make_app()

    async def _enqueue():
        async def noop() -> str:
            return "ok"
        return await wf.enqueue(noop)

    job = asyncio.run(_enqueue())

    with TestClient(app) as client:
        r = client.get(f"/jobs/{job.id}")
        assert r.status_code == 200
        assert r.json()["id"] == job.id


def test_get_missing_job_route():
    app, wf = _make_app()
    with TestClient(app) as client:
        r = client.get("/jobs/nonexistent-id")
        assert r.status_code == 404


def test_cancel_route():
    app, wf = _make_app()
    # Use 0 workers so job stays pending
    wf._queue._workers = 0

    async def _enqueue():
        async def slow() -> None:
            await asyncio.sleep(10)
        return await wf.enqueue(slow)

    job = asyncio.run(_enqueue())
    with TestClient(app) as client:
        r = client.delete(f"/jobs/{job.id}")
        assert r.status_code == 200
        assert r.json()["cancelled"] == job.id


def test_scheduled_route():
    app, wf = _make_app()

    @wf.every(hours=1, name="hourly_task")
    async def hourly() -> None:
        pass

    with TestClient(app) as client:
        r = client.get("/jobs/scheduled")
        assert r.status_code == 200
        names = [j["name"] for j in r.json()]
        assert "hourly_task" in names
