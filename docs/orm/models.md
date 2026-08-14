# Models

Models are SQLAlchemy 2.x declarative classes built on Shakti's `Base`, using `Mapped[T]` annotations and `Field` (Shakti's alias for `mapped_column`).

```python
from __future__ import annotations

from sqlalchemy.orm import Mapped
from shakti.orm import Base, Field, TimestampMixin, String, Text, Boolean, Integer

class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    title: Mapped[str] = Field(String(255), nullable=False)
    body: Mapped[str] = Field(Text, nullable=False)
    views: Mapped[int] = Field(Integer, default=0)
    published: Mapped[bool] = Field(Boolean, default=False)
```

## `Base`

Every model inherits from `shakti.orm.Base`:

- provides an integer autoincrement `id` primary key automatically,
- derives `__tablename__` from the class name if you don't set one explicitly (`BlogPost` → `blog_posts`, snake_case + pluralized with a trailing `s`),
- `.to_dict()` returns every mapped column as a plain dict — handy for returning models straight from a handler,
- a sensible `__repr__` (`<ClassName id=...>`).

## `TimestampMixin`

Mix it in for automatic `created_at` / `updated_at` columns (both timezone-aware `DateTime`, server-defaulted to now, `updated_at` refreshed on every update):

```python
class Comment(TimestampMixin, Base):
    text: Mapped[str] = Field(Text)
```

## `Field` and column types

`Field` is just `sqlalchemy.orm.mapped_column` — anything you'd pass there works (`nullable`, `default`, `unique`, `index`, `server_default`, ...). Common SQLAlchemy column types are re-exported from `shakti.orm` for convenience: `String`, `Text`, `Integer`, `Float`, `Boolean`, `DateTime`, `ForeignKey`, `UniqueConstraint`, plus `relationship` and `Column` for cases `mapped_column` doesn't cover.

```python
from shakti.orm import Field, ForeignKey, relationship

class Comment(TimestampMixin, Base):
    post_id: Mapped[int] = Field(Integer, ForeignKey("posts.id"), nullable=False)
    post: Mapped[Post] = relationship("Post", back_populates="comments")
```

## Nullable / optional fields

Use `T | None` in the `Mapped[...]` annotation together with `nullable=True`:

```python
bio: Mapped[str | None] = Field(Text, nullable=True)
```

## Generating models from the CLI

`shakti generate model` scaffolds a model file from a compact field DSL (`name:type[:modifier...]`) — see [Code Generation](codegen.md) for the full syntax and the combined model+CRUD `generate api` command.

## Querying and mutating

Use a plain SQLAlchemy `select()` against a session (see [Database](database.md)) for full control, or [`Repository`](repository.md) for common CRUD without writing `select()` boilerplate by hand.
