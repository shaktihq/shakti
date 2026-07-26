"""In-memory cache with optional Redis backend.

Usage::

    from shakti.cache import Cache

    cache = Cache()
    cache.init_app(app)

    # Manual get/set
    await cache.set("key", {"data": 1}, ttl=300)
    value = await cache.get("key")

    # Decorator
    @cache.cached(ttl=60)
    async def expensive_query(user_id: int) -> dict:
        ...

    # Redis backend
    cache = Cache(redis_url="redis://localhost:6379")
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shakti.application import Shakti


class Cache:
    """In-memory LRU-style cache. Drop-in Redis when available."""

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = 300,
        max_size: int = 1000,
    ) -> None:
        self.default_ttl = default_ttl
        self.max_size    = max_size
        self._redis_url  = redis_url
        self._redis: Any = None
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)

    def init_app(self, app: Shakti) -> None:
        app.container.register_instance(Cache, self)
        if self._redis_url:
            @app.on_startup
            async def _connect_redis() -> None:
                await self._connect_redis()

    async def _connect_redis(self) -> None:
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(self._redis_url)
        except ImportError:
            import logging
            logging.getLogger("shakti.cache").warning(
                "redis package not installed — using in-memory cache. pip install redis"
            )

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    async def get(self, key: str) -> Any | None:
        if self._redis:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw else None
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        if self._redis:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl or None)
            return
        if len(self._store) >= self.max_size:
            # Evict oldest
            oldest = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest]
        expires_at = time.monotonic() + ttl if ttl else 0
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(key)
        else:
            self._store.pop(key, None)

    async def clear(self) -> None:
        if self._redis:
            await self._redis.flushdb()
        else:
            self._store.clear()

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    # ------------------------------------------------------------------
    # Decorator
    # ------------------------------------------------------------------
    def cached(
        self,
        ttl: int | None = None,
        key_prefix: str = "",
        key_builder: Callable | None = None,
    ) -> Callable:
        """Cache the result of an async function.

        Usage::

            @cache.cached(ttl=300)
            async def get_user(user_id: int) -> dict:
                ...
        """
        _cache = self

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    raw = f"{key_prefix}{func.__module__}.{func.__qualname__}:{args}:{sorted(kwargs.items())}"
                    cache_key = hashlib.md5(raw.encode()).hexdigest()

                cached = await _cache.get(cache_key)
                if cached is not None:
                    return cached

                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result

                await _cache.set(cache_key, result, ttl)
                return result

            wrapper.cache_clear = lambda: _cache.clear()
            return wrapper

        return decorator

    def __repr__(self) -> str:
        backend = f"redis({self._redis_url})" if self._redis_url else "memory"
        return f"<Cache backend={backend} size={len(self._store)}>"
