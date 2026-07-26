"""Core datastructures: headers, query params, and mutable state."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any
from urllib.parse import parse_qsl

from shakti.types import Scope


class Headers:
    """Case-insensitive, read-only view over raw ASGI headers."""

    def __init__(self, raw: list[tuple[bytes, bytes]] | None = None) -> None:
        self._list: list[tuple[bytes, bytes]] = [
            (key.lower(), value) for key, value in (raw or [])
        ]

    @classmethod
    def from_scope(cls, scope: Scope) -> "Headers":
        return cls(list(scope.get("headers") or []))

    @property
    def raw(self) -> list[tuple[bytes, bytes]]:
        return list(self._list)

    def get(self, key: str, default: str | None = None) -> str | None:
        target = key.lower().encode("latin-1")
        for name, value in self._list:
            if name == target:
                return value.decode("latin-1")
        return default

    def getlist(self, key: str) -> list[str]:
        target = key.lower().encode("latin-1")
        return [value.decode("latin-1") for name, value in self._list if name == target]

    def keys(self) -> list[str]:
        return [name.decode("latin-1") for name, _ in self._list]

    def items(self) -> list[tuple[str, str]]:
        return [(name.decode("latin-1"), value.decode("latin-1")) for name, value in self._list]

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._list)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.items()!r})"


class MutableHeaders(Headers):
    """Case-insensitive header collection used when building responses."""

    def set(self, key: str, value: str) -> None:
        target = key.lower().encode("latin-1")
        self._list = [(name, val) for name, val in self._list if name != target]
        self._list.append((target, value.encode("latin-1")))

    def __setitem__(self, key: str, value: str) -> None:
        self.set(key, value)

    def append(self, key: str, value: str) -> None:
        self._list.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    def setdefault(self, key: str, value: str) -> str:
        existing = self.get(key)
        if existing is not None:
            return existing
        self.append(key, value)
        return value

    def update(self, other: Mapping[str, str]) -> None:
        for key, value in other.items():
            self.set(key, value)

    def __delitem__(self, key: str) -> None:
        target = key.lower().encode("latin-1")
        self._list = [(name, val) for name, val in self._list if name != target]


class QueryParams:
    """Parsed query string with multi-value support."""

    def __init__(self, query: str | bytes = "") -> None:
        if isinstance(query, bytes):
            query = query.decode("latin-1")
        self._items: list[tuple[str, str]] = parse_qsl(query, keep_blank_values=True)

    def get(self, key: str, default: str | None = None) -> str | None:
        for name, value in self._items:
            if name == key:
                return value
        return default

    def getlist(self, key: str) -> list[str]:
        return [value for name, value in self._items if name == key]

    def keys(self) -> list[str]:
        return [name for name, _ in self._items]

    def items(self) -> list[tuple[str, str]]:
        return list(self._items)

    def __getitem__(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        return any(name == key for name, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __repr__(self) -> str:
        return f"QueryParams({self._items!r})"


class State:
    """A simple attribute bag for per-request or per-app state."""

    def __init__(self, initial: Mapping[str, Any] | None = None) -> None:
        object.__setattr__(self, "_state", dict(initial or {}))

    def __setattr__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: str) -> Any:
        try:
            return self._state[key]
        except KeyError as exc:
            raise AttributeError(f"State has no attribute {key!r}") from exc

    def __delattr__(self, key: str) -> None:
        try:
            del self._state[key]
        except KeyError as exc:
            raise AttributeError(f"State has no attribute {key!r}") from exc

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._state

    def __repr__(self) -> str:
        return f"State({self._state!r})"
