"""Rate limiting middleware."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable

from shakti.http.request import Request
from shakti.http.response import JSONResponse, Response
from shakti.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit requests per IP address.

    Usage::

        app.add_middleware(RateLimitMiddleware, requests=100, window=60)
        # 100 requests per 60 seconds per IP
    """

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        by: str = "ip",  # ip | route
    ) -> None:
        self.max_requests = requests
        self.window = window
        self.by = by
        self._store: dict[str, list[float]] = defaultdict(list)

    def _get_key(self, request: Request) -> str:
        ip = request.client[0] if request.client else "unknown"
        if self.by == "route":
            return f"{ip}:{request.method}:{request.path}"
        return ip

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        key = self._get_key(request)
        now = time.monotonic()

        # Remove expired timestamps
        self._store[key] = [t for t in self._store[key] if now - t < self.window]

        if len(self._store[key]) >= self.max_requests:
            retry_after = int(self.window - (now - self._store[key][0]))
            return JSONResponse(
                {
                    "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window}s.",
                    "retry_after": retry_after,
                },
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self.window),
                },
            )

        self._store[key].append(now)
        response = await call_next(request)
        remaining = self.max_requests - len(self._store[key])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
