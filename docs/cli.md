# CLI Reference

The `shakti` command handles project scaffolding, running the dev server, and code/migration generation.

```bash
shakti --help
shakti <command> --help
```

## `shakti new`

Scaffold a new project.

```bash
shakti new myapp [--directory .]
```

Generates `app/main.py`, `app/models/`, `config/settings.yaml` + `config/settings.production.yaml`, `tests/test_app.py`, `conftest.py`, `.env`, `.gitignore`, `README.md`, and `requirements.txt`. Fails if the target directory already exists, or if `name` isn't a valid identifier (letters/digits/`-`/`_`, must start with a letter).

## `shakti run`

Start the dev server (uvicorn under the hood).

```bash
shakti run [app] [--host 127.0.0.1] [--port 8000] [--reload] [--workers N]
```

`app` is an import string, default `app.main:app`. `--reload` enables autoreload (mutually exclusive with `--workers` — reload always runs single-process). Requires the `server` extra: `pip install "shakti-framework[server]"`.

## `shakti version`

```bash
shakti version   # prints "shakti <version>"
```

## `shakti generate` (alias `g`)

```bash
shakti generate model <Name> [field:type[:modifier] ...]
shakti generate crud <Name>
shakti generate api <Name> field:type[:modifier] [...]
```

`model` writes a model file; `crud` writes a CRUD router for an existing model; `api` does both in one shot (and requires at least one field). `Name` must be PascalCase. See [Code Generation](orm/codegen.md) for the full field DSL.

## `shakti makemigrations` (alias `mm`)

```bash
shakti makemigrations ["message"]
```

Auto-generates an Alembic migration from the diff between your models and the database. `message` defaults to `"auto"`.

## `shakti migrate`

```bash
shakti migrate [revision]
```

Applies migrations up to `revision` (default `head`, i.e. everything pending).

## `shakti db`

```bash
shakti db history    # list all revisions
shakti db current    # show the currently-applied revision
```

See [Migrations](orm/migrations.md) for how these map to Alembic and what gets generated the first time you run them.

## Typical flow

```bash
shakti new myapp && cd myapp
pip install -r requirements.txt
shakti generate api Post title:str body:text views:int
shakti makemigrations "add posts"
shakti migrate
shakti run --reload
```
