""".env file parsing and ${VAR} interpolation."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

_INTERP_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file. Supports comments, ``export``, and quoted values."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def interpolate(value: str, lookup: Callable[[str], str | None]) -> str:
    """Expand ``${VAR}`` and ``${VAR:default}`` placeholders in a string."""

    def replace(match: re.Match[str]) -> str:
        found = lookup(match.group(1))
        if found is not None:
            return found
        default = match.group(2)
        if default is not None:
            return default
        return match.group(0)

    return _INTERP_PATTERN.sub(replace, value)
