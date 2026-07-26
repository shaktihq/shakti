"""Generic async repository for CRUD operations.

Usage::

    from shakti.orm import Repository
    from app.models import User

    users = Repository(User, session)
    user  = await users.get(1)
    all_  = await users.all()
    found = await users.filter(name="legend")
    new   = await users.create(name="legend", email="a@b.com")
    await  users.update(user, name="Legend")
    await  users.delete(user)
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shakti.orm.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, pk: int) -> ModelT | None:
        return await self.session.get(self.model, pk)

    async def get_or_404(self, pk: int) -> ModelT:
        from shakti.exceptions import HTTPException
        obj = await self.get(pk)
        if obj is None:
            raise HTTPException(404, f"{self.model.__name__} not found")
        return obj

    async def all(self) -> list[ModelT]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def filter(self, **kwargs: Any) -> list[ModelT]:
        stmt = select(self.model)
        for key, value in kwargs.items():
            col = getattr(self.model, key)
            stmt = stmt.where(col == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def first(self, **kwargs: Any) -> ModelT | None:
        results = await self.filter(**kwargs)
        return results[0] if results else None

    async def create(self, **kwargs: Any) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def count(self, **kwargs: Any) -> int:
        return len(await self.filter(**kwargs))

    async def exists(self, **kwargs: Any) -> bool:
        return await self.count(**kwargs) > 0
