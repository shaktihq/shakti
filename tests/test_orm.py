"""Phase 2: ORM + Repository tests using an in-memory SQLite database."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.orm import Mapped

from shakti.orm import Base, Database, Field, Integer, Repository, String, TimestampMixin
from shakti.exceptions import HTTPException


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    title: Mapped[str] = Field(String(255))
    body: Mapped[str] = Field(String(1000), default="")
    views: Mapped[int] = Field(Integer, default=0)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_all(Base)
    yield database
    await database.drop_all(Base)
    await database._engine.dispose()


@pytest_asyncio.fixture()
async def session(db):
    async with db._session_factory() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture()
async def repo(session):
    return Repository(Post, session)


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create(repo):
    post = await repo.create(title="Hello", body="World", views=0)
    assert post.id is not None
    assert post.title == "Hello"


@pytest.mark.asyncio
async def test_get(repo):
    post = await repo.create(title="Get me")
    found = await repo.get(post.id)
    assert found is not None
    assert found.title == "Get me"


@pytest.mark.asyncio
async def test_get_missing_returns_none(repo):
    assert await repo.get(99999) is None


@pytest.mark.asyncio
async def test_get_or_404_raises(repo):
    with pytest.raises(HTTPException) as exc_info:
        await repo.get_or_404(99999)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_all(repo):
    await repo.create(title="A")
    await repo.create(title="B")
    all_posts = await repo.all()
    assert len(all_posts) >= 2


@pytest.mark.asyncio
async def test_filter(repo):
    await repo.create(title="Special", views=999)
    results = await repo.filter(views=999)
    assert len(results) >= 1
    assert all(r.views == 999 for r in results)


@pytest.mark.asyncio
async def test_first(repo):
    await repo.create(title="FindFirst", views=777)
    found = await repo.first(views=777)
    assert found is not None
    assert found.title == "FindFirst"


@pytest.mark.asyncio
async def test_first_missing_returns_none(repo):
    assert await repo.first(views=-1) is None


@pytest.mark.asyncio
async def test_update(repo):
    post = await repo.create(title="Old")
    updated = await repo.update(post, title="New")
    assert updated.title == "New"
    assert updated.id == post.id


@pytest.mark.asyncio
async def test_delete(repo):
    post = await repo.create(title="Delete me")
    pk = post.id
    await repo.delete(post)
    assert await repo.get(pk) is None


@pytest.mark.asyncio
async def test_count(repo):
    await repo.create(title="C1", views=888)
    await repo.create(title="C2", views=888)
    count = await repo.count(views=888)
    assert count >= 2


@pytest.mark.asyncio
async def test_exists(repo):
    await repo.create(title="Exists", views=555)
    assert await repo.exists(views=555) is True
    assert await repo.exists(views=-999) is False


@pytest.mark.asyncio
async def test_to_dict(repo):
    post = await repo.create(title="Dict", body="body text", views=3)
    d = post.to_dict()
    assert d["title"] == "Dict"
    assert d["body"] == "body text"
    assert d["views"] == 3
    assert "id" in d
