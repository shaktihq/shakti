"""Security headers middleware — HSTS, frame options, content sniffing, etc."""

from __future__ import annotations

from shakti.http.request import Request
from shakti.http.response import Response
from shakti.middleware.base import BaseHTTPMiddleware, CallNext


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds common security-related response headers.

    Usage::

        app.add_middleware(SecurityHeadersMiddleware)

    All headers are on by default with conservative values; pass ``None`` to
    a given option to omit that header entirely.
    """

    def __init__(
        self,
        *,
        hsts: bool = True,
        hsts_max_age: int = 31_536_000,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        frame_options: str | None = "DENY",
        content_type_options: bool = True,
        referrer_policy: str | None = "strict-origin-when-cross-origin",
        permissions_policy: str | None = None,
        content_security_policy: str | None = None,
    ) -> None:
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.frame_options = frame_options
        self.content_type_options = content_type_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.content_security_policy = content_security_policy

    def _hsts_value(self) -> str:
        value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            value += "; includeSubDomains"
        if self.hsts_preload:
            value += "; preload"
        return value

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)

        if self.hsts and request.scope.get("scheme") == "https":
            response.headers.setdefault("strict-transport-security", self._hsts_value())
        if self.frame_options:
            response.headers.setdefault("x-frame-options", self.frame_options)
        if self.content_type_options:
            response.headers.setdefault("x-content-type-options", "nosniff")
        if self.referrer_policy:
            response.headers.setdefault("referrer-policy", self.referrer_policy)
        if self.permissions_policy:
            response.headers.setdefault("permissions-policy", self.permissions_policy)
        if self.content_security_policy:
            response.headers.setdefault("content-security-policy", self.content_security_policy)

        return response
