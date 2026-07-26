"""A synchronous test client that drives the ASGI app in-process."""

from __future__ import annotations

import asyncio
import json as jsonlib
from collections.abc import Mapping
from typing import Any, Self
from urllib.parse import urlencode

from shakti.datastructures import Headers
from shakti.types import ASGIApp, Message, Scope


class ClientResponse:
    def __init__(
        self, status_code: int, raw_headers: list[tuple[bytes, bytes]], body: bytes
    ) -> None:
        self.status_code = status_code
        self.headers = Headers(raw_headers)
        self.content = body

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return jsonlib.loads(self.content)

    def __repr__(self) -> str:
        return f"<ClientResponse {self.status_code}>"


class TestClient:
    """Call a Shakti (or any ASGI) app without a running server.

    Use as a context manager to run startup/shutdown hooks::

        with TestClient(app) as client:
            client.get("/health")
    """

    __test__ = False  # prevent pytest from collecting this class

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    # -- lifecycle -----------------------------------------------------
    def __enter__(self) -> Self:
        startup = getattr(self.app, "startup", None)
        if callable(startup):
            asyncio.run(startup())
        return self

    def __exit__(self, *exc_info: object) -> None:
        shutdown = getattr(self.app, "shutdown", None)
        if callable(shutdown):
            asyncio.run(shutdown())

    # -- request API ---------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        query: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Mapping[str, Any] | str | bytes | None = None,
        content: str | bytes | None = None,
    ) -> ClientResponse:
        path, _, query_string = url.partition("?")
        if query:
            encoded = urlencode(query)
            query_string = f"{query_string}&{encoded}" if query_string else encoded

        body = b""
        final_headers: dict[str, str] = {"host": "testserver"}
        if headers:
            final_headers.update({key.lower(): value for key, value in headers.items()})

        if json is not None:
            body = jsonlib.dumps(json).encode("utf-8")
            final_headers.setdefault("content-type", "application/json")
        elif data is not None:
            if isinstance(data, Mapping):
                body = urlencode(data).encode("latin-1")
                final_headers.setdefault(
                    "content-type", "application/x-www-form-urlencoded"
                )
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = bytes(data)
        elif content is not None:
            body = content.encode("utf-8") if isinstance(content, str) else bytes(content)

        if body:
            final_headers.setdefault("content-length", str(len(body)))

        raw_headers = [
            (key.encode("latin-1"), str(value).encode("latin-1"))
            for key, value in final_headers.items()
        ]
        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path or "/",
            "raw_path": (path or "/").encode("latin-1"),
            "query_string": query_string.encode("latin-1"),
            "root_path": "",
            "headers": raw_headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        return asyncio.run(self._send(scope, body))

    async def _send(self, scope: Scope, body: bytes) -> ClientResponse:
        messages: list[Message] = []
        body_sent = False

        async def receive() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            messages.append(message)

        await self.app(scope, receive, send)

        status_code = 500
        raw_headers: list[tuple[bytes, bytes]] = []
        chunks: list[bytes] = []
        for message in messages:
            if message["type"] == "http.response.start":
                status_code = message["status"]
                raw_headers = list(message.get("headers") or [])
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
        return ClientResponse(status_code, raw_headers, b"".join(chunks))

    def get(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("DELETE", url, **kwargs)

    def options(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> ClientResponse:
        return self.request("HEAD", url, **kwargs)
