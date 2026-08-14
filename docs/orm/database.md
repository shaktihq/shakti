# Database

`Database` wraps an async SQLAlchemy engine + session factory and wires session lifecycle into Shakti's startup/shutdown hooks and DI container.

## Setup

```python
from shakti import Shakti, Depends
from shakti.orm import Database
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

app = Shakti()
db = Database("sqlite+aiosqlite:///dev.sqlite3")
db.init_app(app)

@app.get("/users")
async def list_users(session: AsyncSession = Depends(db.get_session)) -> list:
    result = await session.execute(select(User))
    return [u.to_dict() for u in result.scalars()]
```

`init_app`:

- registers `on_startup`/`on_shutdown` hooks (logs a connect message; disposes the engine on shutdown),
- registers `Database` itself in the DI container,
- registers `AsyncSession` in the container as a non-singleton factory, so a plain `session: AsyncSession` handler parameter also works via container injection, without an explicit `Depends(...)`.

Constructor options:

| Parameter | Default | Notes |
|---|---|---|
| `url` | — required | any SQLAlchemy async URL, e.g. `sqlite+aiosqlite:///...`, `postgresql+asyncpg://...` |
| `echo` | `False` | log all SQL statements |
| `pool_size` | `5` | ignored for SQLite |
| `max_overflow` | `10` | ignored for SQLite |
| `pool_pre_ping` | `True` | test connections before use |
| `**engine_kwargs` | — | passed straight through to `create_async_engine` |

## Getting a session

Two ways, depending on how much control you need:

**`db.get_session` as a dependency** — commits automatically on success, rolls back on any exception:

```python
@app.post("/users")
async def create_user(body: dict, session: AsyncSession = Depends(db.get_session)) -> dict:
    user = User(**body)
    session.add(user)
    return user.to_dict()
    # commit happens after this returns; rollback happens if it raises
```

**`db.session()`** — a bare `AsyncSession`, you manage the transaction:

```python
async with db.session() as session:
    session.add(User(email="a@b.com"))
    await session.commit()
```

`Auth` and other framework internals use `db.session()` directly since they need explicit control over commit boundaries — reach for it any time you need more than one commit in a single unit of work.

## Schema helpers

For tests and quick local dev (use [Migrations](migrations.md) for anything you deploy):

```python
await db.create_all()   # CREATE TABLE for everything on Base.metadata
await db.drop_all()     # DROP TABLE for everything on Base.metadata
```

## Accessing the raw engine

```python
db.engine   # AsyncEngine, for anything not covered above
```

See [Models](models.md) for defining tables and [Repository](repository.md) for a higher-level CRUD API built on top of a session.
