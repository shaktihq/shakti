"""Router: registers routes, supports groups, prefixes, and group middleware."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from shakti.exceptions import HTTPException, RouteError
from shakti.routing.route import Route

Endpoint = Callable[..., Any]


def _clean_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    if not prefix.startswith("/"):
        raise RouteError(f"Router prefix must start with '/': {prefix!r}")
    return prefix.rstrip("/")


class Router:
    """A group of routes sharing an optional prefix and middleware stack."""

    def __init__(
        self,
        *,
        prefix: str = "",
        middleware: Sequence[Any] | None = None,
    ) -> None:
        self.prefix = _clean_prefix(prefix)
        self.middleware: list[Any] = list(middleware or [])
        self.routes: list[Route] = []
        self.ws_routes: list[tuple] = []

    def add_route(
        self,
        path: str,
        endpoint: Endpoint,
        *,
        methods: Sequence[str],
        name: str | None = None,
        middleware: Sequence[Any] | None = None,
    ) -> Route:
        if not path.startswith("/"):
            path = "/" + path
        full_path = (self.prefix + path) or "/"
        route = Route(
            full_path,
            endpoint,
            methods,
            name=name,
            middleware=[*self.middleware, *(middleware or [])],
        )
        self.routes.append(route)
        return route

    def route(
        self,
        path: str,
        *,
        methods: Sequence[str],
        name: str | None = None,
        middleware: Sequence[Any] | None = None,
    ) -> Callable[[Endpoint], Endpoint]:
        def decorator(endpoint: Endpoint) -> Endpoint:
            self.add_route(path, endpoint, methods=methods, name=name, middleware=middleware)
            return endpoint

        return decorator

    def get(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["PUT"], **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["DELETE"], **kwargs)

    def options(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["OPTIONS"], **kwargs)

    def head(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.route(path, methods=["HEAD"], **kwargs)

    def include_router(self, router: "Router", *, prefix: str = "") -> None:
        """Mount another router's routes under this router.

        The included routes keep their own prefix; ``prefix`` (and this
        router's prefix) are prepended. Group middleware composes outermost
        (this router) to innermost (the included routes).
        """
        extra = _clean_prefix(prefix)
        for existing in router.routes:
            full_path = (self.prefix + extra + existing.path) or "/"
            route = Route(
                full_path,
                existing.endpoint,
                existing.methods,
                name=existing.name,
                middleware=[*self.middleware, *existing.middleware],
            )
            self.routes.append(route)

    def find(self, method: str, path: str) -> tuple[Route, dict[str, Any]]:
        """Resolve a request to ``(route, path_params)``.

        Raises ``HTTPException(405)`` with an ``Allow`` header when the path
        matches but the method does not, and ``HTTPException(404)`` otherwise.
        """
        allowed: set[str] = set()
        for route in self.routes:
            params = route.match(path)
            if params is None:
                continue
            if method in route.methods:
                return route, params
            allowed |= set(route.methods)
        if allowed:
            raise HTTPException(405, headers={"allow": ", ".join(sorted(allowed))})
        raise HTTPException(404)

    def websocket(self, path: str) -> Any:
        """Register a WebSocket endpoint.

        Usage::

            @app.websocket("/ws/chat")
            async def chat(ws: WebSocket) -> None:
                await ws.accept()
                async for msg in ws.iter_json():
                    await ws.send_json({"echo": msg})
        """
        from shakti.routing.route import compile_path

        def decorator(func: Endpoint) -> Endpoint:
            full_path = _clean_prefix(self.prefix) + path
            pattern, converters = compile_path(full_path)
            self.ws_routes.append((pattern, converters, func))
            return func

        return decorator

    def find_websocket(self, path: str) -> tuple[Any, dict] | None:
        """Find a WebSocket handler for the given path."""
        for pattern, converters, endpoint in self.ws_routes:
            match = pattern.fullmatch(path)
            if match:
                params = {
                    k: converters[k](v) if k in converters else v
                    for k, v in match.groupdict().items()
                }
                return endpoint, params
        return None

    def __repr__(self) -> str:
        return f"<Router prefix={self.prefix!r} routes={len(self.routes)}>"
