"""Cross-Origin Resource Sharing middleware."""

from __future__ import annotations

from collections.abc import Sequence

from shakti.http.request import Request
from shakti.http.response import PlainTextResponse, Response
from shakti.middleware.base import BaseHTTPMiddleware, CallNext

DEFAULT_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


class CORSMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        allow_origins: Sequence[str] = ("*",),
        allow_methods: Sequence[str] = DEFAULT_METHODS,
        allow_headers: Sequence[str] = ("*",),
        allow_credentials: bool = False,
        max_age: int = 600,
    ) -> None:
        self.allow_origins = set(allow_origins)
        self.allow_methods = [method.upper() for method in allow_methods]
        self.allow_headers = list(allow_headers)
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def _origin_allowed(self, origin: str) -> bool:
        return "*" in self.allow_origins or origin in self.allow_origins

    def _allow_origin_value(self, origin: str) -> str:
        if "*" in self.allow_origins and not self.allow_credentials:
            return "*"
        return origin

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        origin = request.headers.get("origin")
        if origin is None:
            return await call_next(request)

        is_preflight = (
            request.method == "OPTIONS"
            and request.headers.get("access-control-request-method") is not None
        )
        if is_preflight:
            if not self._origin_allowed(origin):
                return PlainTextResponse("Disallowed CORS origin", status_code=403)
            if "*" in self.allow_headers:
                allow_headers = request.headers.get(
                    "access-control-request-headers", "*"
                )
            else:
                allow_headers = ", ".join(self.allow_headers)
            headers = {
                "access-control-allow-origin": self._allow_origin_value(origin),
                "access-control-allow-methods": ", ".join(self.allow_methods),
                "access-control-allow-headers": allow_headers,
                "access-control-max-age": str(self.max_age),
                "vary": "Origin",
            }
            if self.allow_credentials:
                headers["access-control-allow-credentials"] = "true"
            return Response(b"", status_code=204, headers=headers)

        response = await call_next(request)
        if self._origin_allowed(origin):
            response.headers.set(
                "access-control-allow-origin", self._allow_origin_value(origin)
            )
            if self.allow_credentials:
                response.headers.set("access-control-allow-credentials", "true")
            response.headers.append("vary", "Origin")
        return response
