"""File upload support — multipart/form-data parsing.

Usage::

    @app.post("/upload")
    async def upload(request: Request) -> dict:
        files = await request.files()
        file = files["document"]
        content = await file.read()
        return {"filename": file.filename, "size": len(content)}

    # Multiple files
    @app.post("/upload-many")
    async def upload_many(request: Request) -> list:
        files = await request.files()
        return [{"name": f.filename, "size": f.size} for f in files.values()]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UploadFile:
    """A file received from a multipart form upload."""

    filename: str
    content_type: str
    content: bytes = field(repr=False)

    @property
    def size(self) -> int:
        return len(self.content)

    async def read(self) -> bytes:
        return self.content

    def __repr__(self) -> str:
        return f"<UploadFile filename={self.filename!r} size={self.size} content_type={self.content_type!r}>"


def parse_multipart(body: bytes, boundary: str) -> dict[str, UploadFile | str]:
    """Parse multipart/form-data body into files and fields."""
    result: dict[str, UploadFile | str] = {}

    sep = f"--{boundary}".encode()
    end = f"--{boundary}--".encode()

    parts = body.split(sep)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--" or part.startswith(end):
            continue

        if b"\r\n\r\n" not in part:
            continue

        headers_raw, _, body_part = part.partition(b"\r\n\r\n")
        body_part = body_part.rstrip(b"\r\n")

        headers: dict[str, str] = {}
        for line in headers_raw.decode("utf-8", errors="replace").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()

        disposition = headers.get("content-disposition", "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        filename_match = re.search(r'filename="([^"]+)"', disposition)

        if not name_match:
            continue

        name = name_match.group(1)
        content_type = headers.get("content-type", "application/octet-stream")

        if filename_match:
            result[name] = UploadFile(
                filename=filename_match.group(1),
                content_type=content_type,
                content=body_part,
            )
        else:
            result[name] = body_part.decode("utf-8", errors="replace")

    return result
