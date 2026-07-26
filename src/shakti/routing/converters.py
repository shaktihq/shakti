"""Path parameter converters: regex fragment + Python caster per type."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

Converter = tuple[str, Callable[[str], Any]]

CONVERTERS: dict[str, Converter] = {
    "str": (r"[^/]+", str),
    "int": (r"[0-9]+", int),
    "float": (r"[0-9]+(?:\.[0-9]+)?", float),
    "uuid": (
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        uuid.UUID,
    ),
    "slug": (r"[a-zA-Z0-9_-]+", str),
    "path": (r".+", str),
}
