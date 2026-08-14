# Repository

`Repository` wraps common CRUD operations for a model + session pair so handlers don't repeat `select()` boilerplate.

```python
from shakti.orm import Repository

users = Repository(User, session)

user  = await users.get(1)               # -> User | None
user  = await users.get_or_404(1)         # -> User, or raises HTTPException(404)
all_  = await users.all()                 # -> list[User]
found = await users.filter(role="admin")  # -> list[User], AND-ed equality filters
one   = await users.first(email="a@b.com")# -> User | None
new   = await users.create(email="a@b.com", username="a")
await   users.update(user, username="renamed")
await   users.delete(user)
count = await users.count(role="admin")
exists = await users.exists(email="a@b.com")
```

`create` and `update` flush and refresh the object immediately, so the returned instance has its generated `id` (and any server-side defaults) populated — you don't need a manual `session.refresh()` afterward. `create`/`update`/`delete` still rely on the surrounding session's commit boundary (see [Database](database.md#getting-a-session)) — nothing is committed until the session itself commits.

## In a handler

Typical pattern: a small dependency that builds a `Repository` bound to the request's session, then inject it:

```python
from shakti import Depends
from shakti.orm import Database, Repository
from sqlalchemy.ext.asyncio import AsyncSession

def _posts(session: AsyncSession = Depends(db.get_session)) -> Repository[Post]:
    return Repository(Post, session)

@app.get("/posts/{id:int}")
async def get_post(id: int, repo: Repository = Depends(_posts)) -> dict:
    post = await repo.get_or_404(id)
    return post.to_dict()

@app.post("/posts")
async def create_post(body: dict, repo: Repository = Depends(_posts)) -> dict:
    post = await repo.create(**body)
    return post.to_dict()
```

This is exactly the pattern `shakti generate crud` / `shakti generate api` scaffold for you automatically — see [Code Generation](codegen.md).

## `filter` semantics

`filter(**kwargs)` builds a `WHERE` clause of `AND`-ed equality comparisons (`column == value` for each kwarg) — it doesn't support `>`, `LIKE`, `OR`, joins, or anything beyond exact-match filtering. For anything more expressive, drop down to SQLAlchemy's `select()` directly against `repo.session` (or just use a session without `Repository` at all — it's a convenience layer, not a required abstraction).

## `get_or_404`

Raises `HTTPException(404, f"{Model.__name__} not found")` when the primary key doesn't exist — handy for the common "fetch or 404" pattern without an explicit `if obj is None: raise ...` in every handler.
