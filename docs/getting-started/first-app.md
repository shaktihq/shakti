---
title: Your First App
description: Step-by-step tutorial for building a real API with Shakti Python Framework — routes, an async ORM model, and a database-backed CRUD endpoint.
---

# Your First App

[Quick Start](quickstart.md) shows the pieces in isolation. This walks through building one small, real app end to end: a notes API backed by a database, with an interactive checkpoint after each step.

## 1. Scaffold the project

```bash
shakti new notes-app
cd notes-app
pip install -r requirements.txt
```

This generates `app/main.py`, `app/models/`, `config/settings.yaml`, and a `tests/` directory — see [Installation](installation.md) if you haven't installed Shakti yet.

## 2. Define a model

```bash
shakti generate model Note title:str body:text
```

This writes `app/models/note.py`:

```python
from __future__ import annotations

from sqlalchemy.orm import Mapped
from shakti.orm import Base, Field, TimestampMixin, String, Text

class Note(TimestampMixin, Base):
    __tablename__ = "notes"

    title: Mapped[str] = Field(String(255))
    body: Mapped[str] = Field(Text)
```

See [Models](../orm/models.md) for what `Base`, `Field`, and `TimestampMixin` give you automatically (an `id` primary key, `created_at`/`updated_at`, and a `to_dict()` helper).

## 3. Wire up the database

In `app/main.py`:

```python
from shakti import Shakti, Depends, HTTPException
from shakti.orm import Database, Repository
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.note import Note

app = Shakti(title="Notes App")

db = Database("sqlite+aiosqlite:///./notes.db")
db.init_app(app)
```

## 4. Add routes

Still in `app/main.py`:

```python
def _notes(session: AsyncSession = Depends(db.get_session)) -> Repository[Note]:
    return Repository(Note, session)

@app.get("/notes")
async def list_notes(repo: Repository = Depends(_notes)) -> list:
    return [n.to_dict() for n in await repo.all()]

@app.post("/notes")
async def create_note(body: dict, repo: Repository = Depends(_notes)) -> dict:
    note = await repo.create(**body)
    return note.to_dict()

@app.get("/notes/{id:int}")
async def get_note(id: int, repo: Repository = Depends(_notes)) -> dict:
    return (await repo.get_or_404(id)).to_dict()
```

This is the same pattern `shakti generate crud` scaffolds automatically — see [Code Generation](../orm/codegen.md) and [Repository](../orm/repository.md) for what `Repository` and `Depends` are doing here.

## 5. Create the table and run

```bash
shakti makemigrations "add notes"
shakti migrate
shakti run --reload
```

Visit `http://127.0.0.1:8000` and try it:

```bash
curl -X POST http://127.0.0.1:8000/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "First note", "body": "Shakti is running."}'

curl http://127.0.0.1:8000/notes
```

## What you just built

A database-backed REST API with three routes, an async ORM model, and automatic request/response handling — no manual session management, no boilerplate serialization.

## Next steps

- Add [JWT authentication](../auth/jwt.md) so notes belong to a logged-in user
- Add an [admin panel](../admin.md) to browse/edit notes without writing UI code
- Add an [AI-powered endpoint](../ai/overview.md) that summarizes a note
- Read [Routing](../core/routing.md) and [Request & Response](../core/request-response.md) for the full HTTP API
