---
description: Quick Start guide for Shakti Python Framework — scaffold a project, add a route, generate a database-backed CRUD API, and enable AI chat in minutes.
---

# Quick Start

## Create a project

```bash
shakti new myapp
cd myapp
pip install -r requirements.txt
shakti run --reload
```

Visit `http://127.0.0.1:8000` — your app is running.

## Add a route

Open `app/main.py`:

```python
@app.get("/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello, {name}!"}
```

## Add a model

```bash
shakti generate api Post title:str body:text views:int
shakti makemigrations "add posts"
shakti migrate
```

Done. You have a full CRUD API at `/posts`.

## Add AI

In `config/settings.yaml`:
```yaml
ai:
  provider: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-sonnet-4-6
```

In `app/main.py`:
```python
from shakti.ai import AI

ai = AI(config)
ai.init_app(app)
```

Now `POST /ai/chat` with `{"message": "Hello!"}` works.
