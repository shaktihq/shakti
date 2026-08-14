"""Response classes that render themselves over ASGI."""

from __future__ import annotations

import asyncio
import json as jsonlib
import os
from collections.abc import Mapping
from mimetypes import guess_type
from typing import Any

from shakti.datastructures import MutableHeaders
from shakti.types import Receive, Scope, Send


class Response:
    """Base response. Subclasses override ``media_type`` and ``render``."""

    media_type: str | None = "text/plain"
    charset: str = "utf-8"

    def __init__(
        self,
        content: Any = b"",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
    ) -> None:
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.body = self.render(content)
        self.headers = MutableHeaders()
        for key, value in (headers or {}).items():
            self.headers.append(key, value)
        if self.media_type is not None and "content-type" not in self.headers:
            content_type = self.media_type
            if content_type.startswith("text/"):
                content_type = f"{content_type}; charset={self.charset}"
            self.headers.set("content-type", content_type)

    def render(self, content: Any) -> bytes:
        if content is None:
            return b""
        if isinstance(content, bytes):
            return content
        if isinstance(content, bytearray):
            return bytes(content)
        if isinstance(content, str):
            return content.encode(self.charset)
        return str(content).encode(self.charset)

    def set_cookie(
        self,
        key: str,
        value: str = "",
        *,
        max_age: int | None = None,
        expires: str | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = "lax",
    ) -> None:
        cookie = f"{key}={value}"
        if max_age is not None:
            cookie += f"; Max-Age={max_age}"
        if expires is not None:
            cookie += f"; Expires={expires}"
        if path:
            cookie += f"; Path={path}"
        if domain:
            cookie += f"; Domain={domain}"
        if secure:
            cookie += "; Secure"
        if httponly:
            cookie += "; HttpOnly"
        if samesite:
            cookie += f"; SameSite={samesite.capitalize()}"
        self.headers.append("set-cookie", cookie)

    def delete_cookie(self, key: str, *, path: str = "/", domain: str | None = None) -> None:
        self.set_cookie(key, "", max_age=0, path=path, domain=domain)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        raw_headers = self.headers.raw
        omit_body = self.status_code < 200 or self.status_code in (204, 304)
        if not omit_body and "content-length" not in self.headers:
            raw_headers.append((b"content-length", str(len(self.body)).encode("latin-1")))
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": raw_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"" if omit_body else self.body,
                "more_body": False,
            }
        )

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.status_code}>"


class PlainTextResponse(Response):
    media_type = "text/plain"


class HTMLResponse(Response):
    media_type = "text/html"


class JSONResponse(Response):
    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        return jsonlib.dumps(
            content, ensure_ascii=False, separators=(",", ":"), default=str
        ).encode("utf-8")


class FileResponse(Response):
    """Streams a file from disk with ``ETag``/``Last-Modified`` validators.

    Callers are responsible for cache-control policy (see
    ``shakti.staticfiles.StaticFiles``); this class only sets the headers
    that describe the file itself.
    """

    chunk_size = 64 * 1024

    def __init__(
        self,
        path: str,
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
    ) -> None:
        self.path = path
        self.filename = filename
        if media_type is None:
            media_type, _ = guess_type(filename or path)
            media_type = media_type or "application/octet-stream"
        self.stat_result = stat_result if stat_result is not None else os.stat(path)
        super().__init__(b"", status_code=status_code, headers=headers, media_type=media_type)
        self.headers.setdefault("content-length", str(self.stat_result.st_size))
        self.headers.setdefault("last-modified", _http_date(self.stat_result.st_mtime))
        self.headers.setdefault("etag", _make_etag(self.stat_result))
        if self.filename:
            self.headers.setdefault(
                "content-disposition", f'inline; filename="{self.filename}"'
            )

    def render(self, content: Any) -> bytes:
        return b""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.headers.raw,
            }
        )
        if self.status_code in (204, 304) or scope.get("method") == "HEAD":
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        sent_any = False
        stream = await asyncio.to_thread(open, self.path, "rb")
        try:
            chunk = await asyncio.to_thread(stream.read, self.chunk_size)
            while chunk:
                sent_any = True
                next_chunk = await asyncio.to_thread(stream.read, self.chunk_size)
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": bool(next_chunk),
                    }
                )
                chunk = next_chunk
        finally:
            await asyncio.to_thread(stream.close)
        if not sent_any:
            await send({"type": "http.response.body", "body": b"", "more_body": False})


def _http_date(timestamp: float) -> str:
    from email.utils import formatdate

    return formatdate(timestamp, usegmt=True)


def _make_etag(stat_result: os.stat_result) -> str:
    return f'"{stat_result.st_mtime_ns:x}-{stat_result.st_size:x}"'


class RedirectResponse(Response):
    media_type = None

    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(content=b"", status_code=status_code, headers=headers)
        self.headers.set("location", url)
