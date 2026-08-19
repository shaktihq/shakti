---
title: Background Jobs & Workflows
description: Background jobs in Shakti Python Framework — an async job queue with automatic retries, exponential backoff, and interval scheduling.
---

# Workflows

`WorkflowEngine` is an in-process background job queue with retries plus a recurring-task scheduler — no separate broker (Redis, RabbitMQ) required.

## Setup

```python
from shakti import WorkflowEngine

workflows = WorkflowEngine(workers=4, max_retries=3, prefix="/jobs")
workflows.init_app(app)
```

`init_app` registers `WorkflowEngine` in the DI container, mounts the [job-management routes](#job-management-routes) under `prefix` (default `/jobs`), and starts/stops the worker pool and scheduler on app startup/shutdown.

## Background jobs

```python
@workflows.job
async def send_email(to: str, subject: str, body: str) -> str:
    # ... send email ...
    return f"Email sent to {to}"

@app.post("/register")
async def register(body: dict) -> dict:
    user = await create_user(body)
    await workflows.enqueue(send_email, to=user["email"], subject="Welcome!", body="Thanks for joining.")
    return {"user": user}
```

`@workflows.job` just marks a function so it shows up in `workflows.stats()`'s `registered_jobs` count — you don't have to decorate a function to enqueue it, but doing so gives you a single place that lists everything schedulable.

`enqueue(func, *, name=None, max_retries=None, delay_seconds=0, **kwargs)` runs `func(**kwargs)` on a worker as soon as one is free (or after `delay_seconds`), retrying up to `max_retries` times (default: the engine's `max_retries`) on failure, and returns a `Job` immediately so you can track it:

```python
job = await workflows.enqueue(send_email, to="a@b.com", subject="Hi", body="...")
job.id       # str — use with workflows.status(job.id)
```

## Job status

```python
job = workflows.status(job_id)   # raises HTTPException(404) if unknown
job.status    # JobStatus: pending | running | completed | failed | retrying | cancelled
job.result    # return value, once completed
job.error     # error message, if failed
job.retries   # attempts so far
```

```python
workflows.cancel(job_id)   # -> bool; only pending jobs can be cancelled
```

## Scheduled (recurring) jobs

```python
@workflows.every(minutes=30)
async def cleanup_sessions() -> None:
    ...

@workflows.every(hours=24)
async def daily_report() -> None:
    ...
```

`every(seconds=, minutes=, hours=, days=, name=None)` — combine units freely (they're summed into one interval); the function runs on that fixed cadence for the lifetime of the app.

## Job-management routes

Mounted under `prefix` (default `/jobs`):

| Route | Does |
|---|---|
| `GET /jobs/` | last 50 jobs |
| `GET /jobs/{job_id}` | one job's status |
| `DELETE /jobs/{job_id}` | cancel (only if still pending) |
| `POST /jobs/{job_id}/retry` | re-queue a failed/cancelled job |
| `GET /jobs/scheduled` | list of recurring jobs |
| `GET /jobs/stats` | queue + scheduler summary |

## Scope and limits

The queue and scheduler are in-process and in-memory — jobs and their history don't survive a restart, and state isn't shared across multiple worker processes. This is a good fit for a single-process deployment doing moderate background work (emails, cleanup tasks, report generation); for durable, multi-process, or high-volume job processing, put a real broker (Redis/Celery/RQ, etc.) behind your own integration instead.
