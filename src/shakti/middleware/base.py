"""HTTP-level middleware operating on Request/Response objects."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from shakti.http.request import Request
from shakti.http.response import Response

CallNext = Callable[[Request], Awaitable[Response]]


class BaseHTTPMiddleware:
    """Subclass and override ``dispatch`` to intercept requests/responses."""

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        return await call_next(request)


def _wrap(middleware: BaseHTTPMiddleware, call_next: CallNext) -> CallNext:
    async def bound(request: Request) -> Response:
        return await middleware.dispatch(request, call_next)

    return bound


def build_middleware_chain(
    endpoint: CallNext, middleware: Sequence[BaseHTTPMiddleware]
) -> CallNext:
    """Compose middleware around an endpoint. First item runs outermost."""
    call: CallNext = endpoint
    for item in reversed(list(middleware)):
        call = _wrap(item, call)
    return call
