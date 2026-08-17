"""Static asset serving with real 404s and fingerprint-aware cache headers.

A missing asset always returns a genuine ``404`` — it is never masked behind
a ``200`` HTML fallback. SPA "serve index.html for anything unknown" support
is opt-in via ``html=True`` and only kicks in for paths that don't look like
asset requests (no dot in the last path segment), so a broken/missing bundle
reference still surfaces as a 404 instead of a silently wrong 200.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from shakti.exceptions import HTTPException
from shakti.http.request import Request
from shakti.http.response import FileResponse, Response

_FINGERPRINT_RE = re.compile(r"\.[0-9a-fA-F]{8,32}\.[^./]+$")


def _looks_fingerprinted(name: str) -> bool:
    """True for filenames like ``app.3f2a9c1e.js`` or ``app-3f2a9c1e8b.css``."""
    return bool(_FINGERPRINT_RE.search(name))


def _extract_hashed_filenames(data: Mapping[str, Any]) -> set[str]:
    """Pull hashed output filenames out of a bundler manifest dict.

    Supports two common shapes, auto-detected per-entry:

    - Vite-style: ``{"src/main.ts": {"file": "assets/main.4889e19a.js",
      "css": ["assets/main.a1b2c3d4.css"], "assets": [...]}}`` — collects
      ``file``, plus every entry in ``css``/``assets``.
    - Flat/Webpack-style: ``{"main.js": "main.4889e19a.js"}`` — the value
      itself is the hashed filename.

    Only the basename is kept, since that's what's compared against the
    requested file's name regardless of how deep the manifest's paths are.
    """
    names: set[str] = set()
    for value in data.values():
        if isinstance(value, str):
            names.add(Path(value).name)
        elif isinstance(value, Mapping):
            file_entry = value.get("file")
            if isinstance(file_entry, str):
                names.add(Path(file_entry).name)
            for key in ("css", "assets"):
                for entry in value.get(key) or ():
                    if isinstance(entry, str):
                        names.add(Path(entry).name)
    return names


def _load_immutable_manifest(manifest: Any) -> set[str] | None:
    """Normalize the ``immutable_manifest`` constructor argument into a
    set of basenames known to be genuinely content-hashed, or ``None`` if
    no manifest was given (caller should fall back to the filename regex).
    """
    if manifest is None:
        return None
    if isinstance(manifest, (str, Path)):
        data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        return _extract_hashed_filenames(data)
    if isinstance(manifest, Mapping):
        return _extract_hashed_filenames(manifest)
    return {Path(name).name for name in manifest}


class StaticFiles:
    """ASGI-style endpoint that serves files out of ``directory``.

    Usage::

        app.static("/assets/{filepath:path}", directory="dist/assets")

    ``max_age`` / ``immutable_max_age`` control ``Cache-Control`` for
    ordinary vs. fingerprinted (content-hashed) files respectively.

    By default, "fingerprinted" is a filename-pattern guess (e.g.
    ``main.9f8c1a2b.js``) — good enough for most setups, but a mutable
    file that happens to look hash-like would be wrongly cached forever.
    Pass ``immutable_manifest`` to make this exact instead of guessed:
    a bundler's manifest (Vite's ``manifest.json``, a Webpack
    ``{name: hashed_name}`` map, a plain iterable of hashed filenames, or
    a path to a JSON file in either shape) becomes the sole source of
    truth for which files get ``immutable`` — anything not listed in it
    gets the regular short-lived ``max_age`` instead, even if its name
    happens to match the fingerprint pattern.

    This also does the right thing across a rolling deployment: an old
    build's still-on-disk hashed asset won't be in the *new* manifest, so
    it falls back to short-lived caching rather than immutable — a small
    efficiency cost for assets from a superseded build, not a
    correctness issue (mixed-version clients still get the right bytes,
    just with a shorter cache lifetime on the outgoing build's files).

    Usage::

        app.static("/assets/{filepath:path}", directory="dist/assets",
                   immutable_manifest="dist/manifest.json")
    """

    def __init__(
        self,
        directory: str | Path,
        *,
        html: bool = False,
        max_age: int = 3600,
        immutable_max_age: int = 31_536_000,
        immutable_manifest: str | Path | Mapping[str, Any] | Iterable[str] | None = None,
    ) -> None:
        self.directory = Path(directory).resolve()
        if not self.directory.is_dir():
            raise HTTPException(500, f"Static directory not found: {self.directory}")
        self.html = html
        self.max_age = max_age
        self.immutable_max_age = immutable_max_age
        self._immutable_names = _load_immutable_manifest(immutable_manifest)

    def _resolve(self, filepath: str) -> Path:
        """Resolve ``filepath`` under ``directory``, rejecting traversal."""
        candidate = (self.directory / filepath.lstrip("/")).resolve()
        try:
            candidate.relative_to(self.directory)
        except ValueError:
            raise HTTPException(404) from None
        return candidate

    def _is_immutable(self, name: str) -> bool:
        if self._immutable_names is not None:
            return name in self._immutable_names
        return _looks_fingerprinted(name)

    def _cache_control(self, name: str) -> str:
        if self._is_immutable(name):
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
