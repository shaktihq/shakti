---
description: Database migrations in Shakti Python Framework — Alembic integration via the shakti CLI, from makemigrations to deploy.
---

# Migrations

Shakti wraps [Alembic](https://alembic.sqlalchemy.org/) so you get schema migrations without hand-writing `alembic.ini`/`env.py` — everything's driven from the `shakti` CLI.

```bash
shakti makemigrations "add posts table"   # alias: shakti mm
shakti migrate                            # apply pending migrations, alias target defaults to head
```

## What happens under the hood

The first time you run `makemigrations` or `migrate`, Shakti generates (idempotently — it won't overwrite an existing setup):

- `migrations/env.py` — an async-aware Alembic environment that imports `app.models` (so Alembic sees your metadata) and reads the database URL from your `Config` (`database.url`),
- `migrations/script.py.mako` — the template used for each new revision file,
- `alembic.ini` — pointed at `migrations/` as the script location.

You can edit any of these afterward; regeneration only happens if they're missing.

## Commands

| Command | Alembic equivalent | Notes |
|---|---|---|
| `shakti makemigrations [message]` | `alembic revision --autogenerate -m ...` | diffs your models against the DB and writes a new revision file. `message` defaults to `"auto"`. |
| `shakti migrate [revision]` | `alembic upgrade <revision>` | applies migrations up to `revision` (defaults to `head`, i.e. everything pending). |
| `shakti db history` | `alembic history` | list revisions. |
| `shakti db current` | `alembic current -v` | show the currently-applied revision. |

Autogeneration is exactly Alembic's — meaning it's good at columns/tables/indexes, but you should always eyeball the generated migration file before running it (Alembic can't reliably detect renames, certain type changes, or data migrations).

## Requirements

Migrations need the `orm` extra:

```bash
pip install "shakti-framework[orm]"   # sqlalchemy[asyncio], alembic, aiosqlite
```

## Typical flow

```bash
# 1. define/change a model in app/models/
# 2. generate a migration from the diff
shakti makemigrations "add published flag to posts"
# 3. review migrations/versions/<generated>.py
# 4. apply it
shakti migrate
```

See [Models](models.md) for how model classes map to tables, and [Database](database.md#schema-helpers) for `create_all()`/`drop_all()` — quick schema helpers for tests, not a substitute for migrations in anything you deploy.
