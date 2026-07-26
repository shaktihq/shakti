"""A single route: compiled path pattern + endpoint + allowed methods."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from shakti.exceptions import RouteError
from shakti.routing.converters import CONVERTERS

PARAM_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_]+))?\}")


def compile_path(path: str) -> tuple[re.Pattern[str], dict[str, Callable[[str], Any]]]:
    """Compile ``/users/{user_id:int}`` into a regex + converter map."""
    if not path.startswith("/"):
        raise RouteError(f"Route path must start with '/': {path!r}")

    regex_parts: list[str] = ["^"]
    converters: dict[str, Callable[[str], Any]] = {}
    index = 0

    for match in PARAM_PATTERN.finditer(path):
        name = match.group(1)
        converter_name = match.group(2) or "str"
        if converter_name not in CONVERTERS:
            raise RouteError(f"Unknown path converter {converter_name!r} in {path!r}")
        if name in converters:
            raise RouteError(f"Duplicate path parameter {name!r} in {path!r}")
        pattern, converter = CONVERTERS[converter_name]
        regex_parts.append(re.escape(path[index : match.start()]))
        regex_parts.append(f"(?P<{name}>{pattern})")
        converters[name] = converter
        index = match.end()

    regex_parts.append(re.escape(path[index:]))
    regex_parts.append("$")
    return re.compile("".join(regex_parts)), converters


class Route:
    """An HTTP route bound to an endpoint callable."""

    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: Iterable[str],
        *,
        name: str | None = None,
        middleware: Sequence[Any] | None = None,
    ) -> None:
        self.path = path
        self.endpoint = endpoint
        method_set = {method.upper() for method in methods}
        if "GET" in method_set:
            method_set.add("HEAD")
        self.methods: frozenset[str] = frozenset(method_set)
        self.name = name or getattr(endpoint, "__name__", "route")
        self.middleware: list[Any] = list(middleware or [])
        self.pattern, self.param_converters = compile_path(path)

    def match(self, path: str) -> dict[str, Any] | None:
        """Return converted path params if ``path`` matches, else ``None``."""
        matched = self.pattern.match(path)
        if matched is None:
            return None
        params: dict[str, Any] = {}
        for key, value in matched.groupdict().items():
            try:
                params[key] = self.param_converters[key](value)
            except ValueError:
                return None
        return params

    def __repr__(self) -> str:
        methods = ",".join(sorted(self.methods))
        return f"<Route {methods} {self.path} -> {self.name}>"
