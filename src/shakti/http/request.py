"""The Request object wrapping an ASGI HTTP scope."""

from __future__ import annotations

import json as jsonlib
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qsl

from shakti.datastructures import Headers, QueryParams, State
from shakti.exceptions import HTTPException
from shakti.types import Receive, Scope


class Request:
    """Lazy, cached access to everything about the incoming HTTP request."""

    __slots__ = (
        "scope",
        "state",
        "path_params",
        "_receive",
        "_body",
        "_headers",
        "_query_params",
        "_cookies",
        "_depends_cache",
    )

    def __init__(self, scope: Scope, receive: Receive) -> None:
        self.scope = scope
        self.state = State()
        self.path_params: dict[str, Any] = {}
        self._receive = receive
        self._body: bytes | None = None
        self._headers: Headers | None = None
        self._query_params: QueryParams | None = None
        self._cookies: dict[str, str] | None = None
        self._depends_cache: dict[Any, Any] = {}

    @property
    def app(self) -> Any:
        return self.scope.get("app")

    @property
    def method(self) -> str:
        return str(self.scope["method"]).upper()

    @property
    def path(self) -> str:
        return str(self.scope.get("path", "/"))

    @property
    def query_string(self) -> bytes:
        return bytes(self.scope.get("query_string", b""))

    @property
    def headers(self) -> Headers:
        if self._headers is None:
            self._headers = Headers.from_scope(self.scope)
        return self._headers

    @property
    def query_params(self) -> QueryParams:
        if self._query_params is None:
            self._query_params = QueryParams(self.query_string)
        return self._query_params

    @property
    def cookies(self) -> dict[str, str]:
        if self._cookies is None:
            cookies: dict[str, str] = {}
            header = self.headers.get("cookie")
            if header:
                jar: SimpleCookie = SimpleCookie()
                jar.load(header)
                cookies = {key: morsel.value for key, morsel in jar.items()}
            self._cookies = cookies
        return self._cookies

    @property
    def content_type(self) -> str:
        raw = self.headers.get("content-type", "") or ""
        return raw.split(";", 1)[0].strip().lower()

    @property
    def client(self) -> tuple[str, int] | None:
        client = self.scope.get("client")
        return (client[0], client[1]) if client else None

    async def body(self) -> bytes:
        if self._body is None:
            chunks: list[bytes] = []
            while True:
                message = await self._receive()
                if message["type"] == "http.request":
                    chunks.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    break
            self._body = b"".join(chunks)
        return self._body

    async def json(self) -> Any:
        raw = await self.body()
        if not raw:
            raise HTTPException(400, "Request body is empty; expected JSON")
        try:
            return jsonlib.loads(raw)
        except ValueError as exc:
            raise HTTPException(400, "Malformed JSON in request body") from exc

    async def form(self) -> dict[str, str]:
        content_type = self.content_type
        if content_type == "application/x-www-form-urlencoded":
            raw = await self.body()
            return dict(parse_qsl(raw.decode("latin-1"), keep_blank_values=True))
        if content_type.startswith("multipart/"):
            raise HTTPException(
                415,
                "multipart/form-data is not supported; "
                "send application/x-www-form-urlencoded or JSON",
            )
        raise HTTPException(415, f"Unsupported form content type: {content_type or 'unknown'}")

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"
