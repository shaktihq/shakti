"""Static asset serving with real 404s and fingerprint-aware cache headers.

A missing asset always returns a genuine ``404`` — it is never masked behind
a ``200`` HTML fallback. SPA "serve index.html for anything unknown" support
is opt-in via ``html=True`` and only kicks in for paths that don't look like
asset requests (no dot in the last path segment), so a broken/missing bundle
reference still surfaces as a 404 instead of a silently wrong 200.
"""

from __future__ import annotations

import re
from pathlib import Path

from shakti.exceptions import HTTPException
from shakti.http.request import Request
from shakti.http.response import FileResponse, Response

_FINGERPRINT_RE = re.compile(r"\.[0-9a-fA-F]{8,32}\.[^./]+$")


def _looks_fingerprinted(name: str) -> bool:
    """True for filenames like ``app.3f2a9c1e.js`` or ``app-3f2a9c1e8b.css``."""
    return bool(_FINGERPRINT_RE.search(name))


class StaticFiles:
    """ASGI-style endpoint that serves files out of ``directory``.

    Usage::

        app.static("/assets/{filepath:path}", directory="dist/assets")

    ``max_age`` / ``immutable_max_age`` control ``Cache-Control`` for
    ordinary vs. fingerprinted (content-hashed) files respectively.
    Fingerprinted files are detected by filename pattern (e.g.
    ``main.9f8c1a2b.js``) and served with ``public, immutable``.
    """

    def __init__(
        self,
        directory: str | Path,
        *,
        html: bool = False,
        max_age: int = 3600,
        immutable_max_age: int = 31_536_000,
    ) -> None:
        self.directory = Path(directory).resolve()
        if not self.directory.is_dir():
            raise HTTPException(500, f"Static directory not found: {self.directory}")
        self.html = html
        self.max_age = max_age
        self.immutable_max_age = immutable_max_age

    def _resolve(self, filepath: str) -> Path:
        """Resolve ``filepath`` under ``directory``, rejecting traversal."""
        candidate = (self.directory / filepath.lstrip("/")).resolve()
        try:
            candidate.relative_to(self.directory)
        except ValueError:
            raise HTTPException(404) from None
        return candidate

    def _cache_control(self, name: str) -> str:
        if _looks_fingerprinted(name):
            return f"public, max-age={self.immutable_max_age}, immutable"
        return f"public, max-age={self.max_age}"

    async def __call__(self, request: Request, filepath: str = "") -> Response:
        target = self._resolve(filepath)

        if not target.is_file():
            if self.html and "." not in target.name:
                index = self.directory / "index.html"
                if index.is_file():
                    response = FileResponse(str(index))
                    response.headers.set("cache-control", "no-cache")
                    return response
            raise HTTPException(404)

        stat_result = target.stat()
        response = FileResponse(str(target), stat_result=stat_result)

        etag = response.headers.get("etag")
        if etag is not None and request.headers.get("if-none-match") == etag:
            return Response(b"", status_code=304, headers=dict(response.headers.items()))

        response.headers.set("cache-control", self._cache_control(target.name))
        return response
