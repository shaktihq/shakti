---
title: Build a REST API with Shakti
description: Tutorial — build a database-backed REST API in Python with Shakti Python Framework, from project scaffold to a working CRUD endpoint.
---

# Build a REST API with Shakti

This walks through building a small task-tracking REST API with Shakti Python Framework — a database-backed resource with full CRUD, in well under a hundred lines.

## Scaffold the project

```bash
shakti new task-api
cd task-api
pip install -r requirements.txt
```

## Generate a model and CRUD router in one command

Shakti can scaffold both the model and the router from a field spec:

```bash
shakti generate api Task title:str done:bool priority:int
```

This writes `app/models/task.py` (a SQLAlchemy model with `title`, `done`, `priority`, plus an auto-added `id` and timestamps) and `app/routers/task.py` (a full CRUD router: list, create, get, update, delete). See [Code Generation](../orm/codegen.md) for the exact field DSL.

## Wire it up

In `app/main.py`:

```python
from app.routers.task import router as task_router
app.include_router(task_router)
```

## Create the table

```bash
shakti makemigrations "add tasks"
shakti migrate
shakti run --reload
```

## Use it

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Ship the API", "done": false, "priority": 1}'

curl http://127.0.0.1:8000/tasks
curl http://127.0.0.1:8000/tasks/1
curl -X PUT http://127.0.0.1:8000/tasks/1 -d '{"done": true}'
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

Five working REST endpoints, backed by a real database, from one CLI command plus a router include.

## What's actually happening under the hood

The generated router uses [`Repository`](../orm/repository.md) for the database work and Shakti's [dependency injection](../core/di.md) to hand each handler a session-bound repository — no manual session management in your own code:

```python
@router.get("/{id:int}")
async def get_task(id: int, repo: Repository = Depends(_repo)) -> dict:
    return (await repo.get_or_404(id)).to_dict()
```

`get_or_404` raises a proper `404` automatically if the row doesn't exist — see [Request & Response](../core/request-response.md) for how error handling works across the framework.

## Next: lock it down and add AI

A public CRUD API is a starting point, not an endpoint. From here:

- Add [JWT authentication](../auth/jwt.md) so only logged-in users can create or modify tasks
- Add [rate limiting](../core/middleware.md#ratelimitmiddleware) to the public routes
- Add an AI endpoint that prioritizes tasks automatically — see [Build an AI Agent with Shakti](build-ai-agent-with-shakti.md)
- Browse and edit tasks visually with the [admin panel](shakti-admin-panel.md)
