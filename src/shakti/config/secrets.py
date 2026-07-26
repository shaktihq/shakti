"""Secret wrapper that never leaks its value through repr/str/logging."""

from __future__ import annotations

from typing import Any


class Secret:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret('**********')"

    def __str__(self) -> str:
        return "**********"

    def __bool__(self) -> bool:
        return bool(self._value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Secret):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)
