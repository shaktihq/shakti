"""In-memory Cache: TTL expiry and LRU eviction."""

from __future__ import annotations

import asyncio

from shakti.cache import Cache


def run(coro):
    return asyncio.run(coro)


def test_get_set_roundtrip() -> None:
    cache = Cache()

    async def _run():
        await cache.set("a", {"x": 1})
        return await cache.get("a")

    assert run(_run()) == {"x": 1}


def test_missing_key_returns_none() -> None:
    cache = Cache()
    assert run(cache.get("missing")) is None


def test_ttl_expiry() -> None:
    cache = Cache()

    async def _run():
        await cache.set("a", "value", ttl=0.05)
        immediate = await cache.get("a")
        await asyncio.sleep(0.1)
        later = await cache.get("a")
        return immediate, later

    immediate, later = run(_run())
    assert immediate == "value"
    assert later is None


def test_eviction_is_least_recently_used_not_soonest_to_expire() -> None:
    """Regression test: eviction must be LRU, not soonest-expiry-first.

    Previously ``set()`` evicted whichever entry had the smallest
    ``expires_at`` — which meant a permanent entry (ttl=0, expires_at=0)
    was always evicted first, and access order was never tracked at all.
    """
    cache = Cache(max_size=2, default_ttl=300)

    async def _run():
        await cache.set("permanent", "keep-me", ttl=0)  # no expiry
        await cache.set("short", "b", ttl=9999)  # longer ttl than "permanent"'s 0
        # Touch "permanent" so it's the most-recently-used.
        await cache.get("permanent")
        # Adding a third key must evict "short" (least-recently-used),
        # not "permanent" (which merely has the smallest expires_at).
        await cache.set("newest", "c")
        return await cache.get("permanent"), await cache.get("short"), await cache.get("newest")

    permanent, short, newest = run(_run())
    assert permanent == "keep-me"
    assert short is None
    assert newest == "c"


def test_set_on_existing_key_refreshes_lru_position() -> None:
    cache = Cache(max_size=2)

    async def _run():
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.set("a", 100)  # re-set "a" — should become most-recently-used
        await cache.set("c", 3)  # must evict "b", not "a"
        return await cache.get("a"), await cache.get("b"), await cache.get("c")

    a, b, c = run(_run())
    assert a == 100
    assert b is None
    assert c == 3


def test_cached_decorator() -> None:
    cache = Cache()
    calls = {"n": 0}

    @cache.cached(ttl=60)
    async def expensive(x: int) -> int:
        calls["n"] += 1
        return x * 2

    async def _run():
        first = await expensive(5)
        second = await expensive(5)
        return first, second

    first, second = run(_run())
    assert first == second == 10
    assert calls["n"] == 1
