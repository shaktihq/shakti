"""Async database engine + session factory, integrated with Shakti's DI.

Usage in app/main.py::

    from shakti.orm import Database
    from app.models import Base          # imports all models

    db = Database("sqlite+aiosqlite:///dev.sqlite3")
    app = Shakti()
    db.init_app(app)                     # registers startup/shutdown hooks

    @app.get("/users")
    async def list_users(session: AsyncSession = Depends(db.get_session)) -> list:
        result = await session.execute(select(User))
        return [u.to_dict() for u in result.scalars()]
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shakti.orm.base import Base

if TYPE_CHECKING:
    from shakti.application import Shakti

logger = logging.getLogger("shakti.orm")


class Database:
    """Manages the async SQLAlchemy engine and session lifecycle."""

    def __init__(
        self,
        url: str,
        *,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        **engine_kwargs: Any,
    ) -> None:
        self.url = url
        self._echo = echo
        kwargs: dict[str, Any] = {
            "echo": echo,
            "pool_pre_ping": pool_pre_ping,
            **engine_kwargs,
        }
        # SQLite doesn't support pool_size / max_overflow
        if not url.startswith("sqlite"):
            kwargs.update(pool_size=pool_size, max_overflow=max_overflow)
        self._engine: AsyncEngine = create_async_engine(url, **kwargs)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._app: Shakti | None = None

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: Shakti) -> None:
        """Register startup / shutdown hooks and inject session into the DI container."""
        self._app = app

        @app.on_startup
        async def _startup() -> None:
            logger.info("Database connected: %s", self._sanitize_url())

        @app.on_shutdown
        async def _shutdown() -> None:
            await self._engine.dispose()
            logger.info("Database disconnected")

        app.container.register_instance(Database, self)
        app.container.register(AsyncSession, factory=self._create_session, singleton=False)

    async def _create_session(self) -> AsyncSession:
        return self._session_factory()

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency: yields an ``AsyncSession``, commits on success, rolls back on error."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def session(self) -> AsyncSession:
        """Return a bare ``AsyncSession`` (caller manages commit/rollback)."""
        return self._session_factory()

    # ------------------------------------------------------------------
    # Schema helpers (useful in tests / dev)
    # ------------------------------------------------------------------
    async def create_all(self, base: type = Base) -> None:
        """Create all tables declared on *base*."""
        async with self._engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    async def drop_all(self, base: type = Base) -> None:
        """Drop all tables declared on *base*."""
        async with self._engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _sanitize_url(self) -> str:
        from urllib.parse import urlparse, urlunparse
        try:
            p = urlparse(self.url)
            safe = p._replace(netloc=p.netloc.split("@")[-1] if "@" in p.netloc else p.netloc)
            return urlunparse(safe)
        except Exception:
            return "<url>"

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def __repr__(self) -> str:
        return f"Database(url={self._sanitize_url()!r})"
