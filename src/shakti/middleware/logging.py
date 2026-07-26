"""Access-log middleware built on the standard library logger."""

from __future__ import annotations

import logging
import time

from shakti.http.request import Request
from shakti.http.response import Response
from shakti.middleware.base import BaseHTTPMiddleware, CallNext


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("shakti.access")

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._logger.exception("%s %s -> unhandled error", request.method, request.path)
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        self._logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
