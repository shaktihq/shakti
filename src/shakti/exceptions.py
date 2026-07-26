"""Exception hierarchy for Shakti."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus


class ShaktiError(Exception):
    """Base class for all Shakti errors."""


class ConfigError(ShaktiError):
    """Raised when configuration is missing or invalid."""


class RouteError(ShaktiError):
    """Raised when a route definition is invalid."""


class HTTPException(ShaktiError):
    """An error that maps directly to an HTTP response.

    Raise it anywhere inside a handler, dependency, or middleware and the
    application converts it into a JSON error response.
    """

    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if detail is None:
            try:
                detail = HTTPStatus(status_code).phrase
            except ValueError:
                detail = "Error"
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.headers: dict[str, str] = dict(headers or {})

    def __repr__(self) -> str:
        return f"HTTPException(status_code={self.status_code}, detail={self.detail!r})"
