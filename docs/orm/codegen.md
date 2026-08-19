---
description: Generate models and CRUD routers in Shakti Python Framework with one CLI command — shakti generate api, model, or crud.
---

# Code Generation

`shakti generate` (alias `shakti g`) scaffolds models and CRUD routers from a compact field DSL, so a full REST resource is a one-liner.

```bash
shakti generate api Post title:str body:text views:int published:bool
```

This writes both a model (`app/models/post.py`) and a CRUD router (`app/routers/post.py`), and registers the model import in `app/models/__init__.py` so Alembic picks it up.

## `kind` options

```bash
shakti generate model Post title:str body:text   # model only
shakti generate crud Post                         # router only (model must already exist)
shakti generate api Post title:str body:text      # both
```

## Field DSL

```
name:type[:modifier[:modifier...]]
```

| Type | Python | SQLAlchemy column |
|---|---|---|
| `str` (default if omitted) | `str` | `String(255)` |
| `text` | `str` | `Text` |
| `int` | `int` | `Integer` |
| `float` | `float` | `Float` |
| `bool` | `bool` | `Boolean` (defaults to `False`) |
| `datetime` | `datetime` | `DateTime(timezone=True)` |
| `uuid` | `str` | `String(36)`, unique |

Modifiers (combine with more `:`): `unique`, `nullable`, `index`.

```bash
shakti generate model User email:str:unique bio:text:nullable age:int:index
```

```python
# generated app/models/user.py
class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = Field(String(255), unique=True)
    bio: Mapped[str | None] = Field(Text, nullable=True)
    age: Mapped[int] = Field(Integer, index=True)

    def __repr__(self) -> str:
        return f"<User id={self.id}>"
```

Generated models include `TimestampMixin` (`created_at`/`updated_at`) by default.

## Generated CRUD router

`generate crud Post` (or the CRUD half of `generate api`) produces a full `Router` at `/posts` using [`Repository`](repository.md):

```python
router = Router(prefix="/posts")

@router.get("/")            # list
@router.get("/{id:int}")    # get_or_404
@router.post("/")           # create
@router.put("/{id:int}")    # update
@router.delete("/{id:int}") # delete
```

Wire it up like any other router:

```python
from app.routers.post import router as post_router
app.include_router(post_router)
```

## After generating

```bash
shakti makemigrations "add posts"
shakti migrate
```

Generated files are plain Python — nothing generated is regenerated in place, so edit freely once written. See [Quick Start](../getting-started/quickstart.md) for this same flow end-to-end, and [Migrations](migrations.md) for what `makemigrations`/`migrate` actually do.
