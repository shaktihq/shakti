"""The Shakti application: an ASGI app tying every subsystem together."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable, Sequence
from typing import Any

from shakti.config.settings import Config
from shakti.di import Container, _maybe_await, call_with_injection
from shakti.exceptions import HTTPException
from shakti.http.request import Request
from shakti.http.response import JSONResponse, PlainTextResponse, Response
from shakti.middleware.base import BaseHTTPMiddleware, build_middleware_chain
from shakti.routing.router import Endpoint, Router
from shakti.types import Receive, Scope, Send
from shakti.websocket import WebSocket, WebSocketDisconnect

logger = logging.getLogger("shakti.app")

ExceptionHandler = Callable[[Request, BaseException], Any]
LifecycleHook = Callable[[], Any]


def coerce_response(result: Any) -> Response:
    """Convert a handler return value into a Response.

    Supported: Response, None (204), dict/list (JSON), str (plain text),
    bytes, and ``(body, status_code)`` tuples.
    """
    if isinstance(result, Response):
        return result
    if result is None:
        return Response(b"", status_code=204)
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[1], int)
    ):
        response = coerce_response(result[0])
        response.status_code = result[1]
        return response
    if isinstance(result, (dict, list)):
        return JSONResponse(result)
    if isinstance(result, str):
        return PlainTextResponse(result)
    if isinstance(result, (bytes, bytearray)):
        return Response(bytes(result), media_type="application/octet-stream")
    return JSONResponse(result)


class Shakti:
    """The core application class.

    Usage::

        app = Shakti(title="My API")

        @app.get("/")
        async def index() -> dict:
            return {"hello": "world"}
    """

    def __init__(
        self,
        *,
        title: str = "Shakti",
        version: str = "0.1.0",
        debug: bool | None = None,
        config: Config | None = None,
    ) -> None:
        self.title = title
        self.version = version
        self.config = config if config is not None else Config()
        self.debug = (
            debug
            if debug is not None
            else bool(self.config.get("app.debug", False, cast=bool))
        )
        self.router = Router()
        self.container = Container()
        self.state: Any = _AppState()
        self._middleware: list[BaseHTTPMiddleware] = []
        self._exception_handlers: dict[type[BaseException], ExceptionHandler] = {}
        self._startup_hooks: list[LifecycleHook] = []
        self._shutdown_hooks: list[LifecycleHook] = []
        self._started = False

        self.container.register_instance(Config, self.config)
        self.container.register_instance(Shakti, self)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def route(self, path: str, *, methods: Sequence[str], **kwargs: Any) -> Any:
        return self.router.route(path, methods=methods, **kwargs)

    def get(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.put(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.delete(path, **kwargs)

    def options(self, path: str, **kwargs: Any) -> Callable[[Endpoint], Endpoint]:
        return self.router.options(path, **kwargs)

    def websocket(self, path: str) -> Any:
        """Register a WebSocket endpoint.

        Usage::

            @app.websocket("/ws/chat")
            async def chat(ws: WebSocket) -> None:
                await ws.accept()
                async for msg in ws.iter_json():
                    await ws.send_json({"echo": msg})
        """
        return self.router.websocket(path)

    def include_router(self, router: Router, *, prefix: str = "") -> None:
        self.router.include_router(router, prefix=prefix)

    # ------------------------------------------------------------------
    # Middleware & error handling
    # ------------------------------------------------------------------
    def add_middleware(
        self, middleware: type[BaseHTTPMiddleware] | BaseHTTPMiddleware, **options: Any
    ) -> None:
        """Add app-level middleware. First added runs outermost."""
        if isinstance(middleware, type):
            instance = middleware(**options)
        else:
            if options:
                raise TypeError(
                    "Options are only accepted when passing a middleware class"
                )
            instance = middleware
        self._middleware.append(instance)

    def exception_handler(
        self, exc_class: type[BaseException]
    ) -> Callable[[ExceptionHandler], ExceptionHandler]:
        def decorator(handler: ExceptionHandler) -> ExceptionHandler:
            self._exception_handlers[exc_class] = handler
            return handler

        return decorator

    def _lookup_exception_handler(
        self, exc_type: type[BaseException]
    ) -> ExceptionHandler | None:
        for klass in exc_type.__mro__:
            if klass in self._exception_handlers:
                return self._exception_handlers[klass]
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_startup(self, func: LifecycleHook) -> LifecycleHook:
        self._startup_hooks.append(func)
        return func

    def on_shutdown(self, func: LifecycleHook) -> LifecycleHook:
        self._shutdown_hooks.append(func)
        return func

    def on_event(self, event: str) -> Callable[[LifecycleHook], LifecycleHook]:
        if event == "startup":
            return self.on_startup
        if event == "shutdown":
            return self.on_shutdown
        raise ValueError(f"Unknown lifecycle event: {event!r}")

    async def startup(self) -> None:
        if self._started:
            return
        for hook in self._startup_hooks:
            await _maybe_await(hook())
        self._started = True

    async def shutdown(self) -> None:
        if not self._started:
            return
        for hook in self._shutdown_hooks:
            await _maybe_await(hook())
        self._started = False

    # ------------------------------------------------------------------
    # ASGI entrypoint
    # ------------------------------------------------------------------
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope_type = scope["type"]
        if scope_type == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope_type == "websocket":
            await self._handle_websocket(scope, receive, send)
            return
        if scope_type != "http":
            raise RuntimeError(
                f"Shakti does not support ASGI scope type {scope_type!r} yet"
            )
        scope["app"] = self
        request = Request(scope, receive)
        try:
            response = await self._handle(request)
        except Exception:
            logger.exception(
                "Unrecoverable error handling %s %s", request.method, request.path
            )
            response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)
        await response(scope, receive, send)

    async def _lifespan(self, receive: Receive, send: Send) -> None:
        await receive()  # lifespan.startup
        try:
            await self.startup()
        except Exception as exc:
            logger.exception("Application startup failed")
            await send({"type": "lifespan.startup.failed", "message": str(exc)})
            return
        await send({"type": "lifespan.startup.complete"})
        await receive()  # lifespan.shutdown
        try:
            await self.shutdown()
        except Exception as exc:
            logger.exception("Application shutdown failed")
            await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
            return
        await send({"type": "lifespan.shutdown.complete"})

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------
    async def _route_and_dispatch(self, request: Request) -> Response:
        route, params = self.router.find(request.method, request.path)
        request.path_params = params
        request.scope["route"] = route

        async def endpoint(req: Request) -> Response:
            result = await call_with_injection(route.endpoint, req, self.container)
            return coerce_response(result)

        chain = build_middleware_chain(endpoint, route.middleware)
        return await chain(request)

    async def _safe_dispatch(self, request: Request) -> Response:
        """Route + dispatch, converting exceptions into responses so that
        app-level middleware (e.g. CORS) also sees error responses."""
        try:
            return await self._route_and_dispatch(request)
        except HTTPException as exc:
            return await self._render_http_exception(request, exc)
        except Exception as exc:
            return await self._render_unhandled(request, exc)

    async def _handle(self, request: Request) -> Response:
        chain = build_middleware_chain(self._safe_dispatch, self._middleware)
        try:
            response = await chain(request)
        except HTTPException as exc:
            response = await self._render_http_exception(request, exc)
        except Exception as exc:
            response = await self._render_unhandled(request, exc)
        if request.method == "HEAD":
            response.body = b""
        return response

    async def _render_http_exception(
        self, request: Request, exc: HTTPException
    ) -> Response:
        handler = self._lookup_exception_handler(type(exc))
        if handler is not None:
            return coerce_response(await _maybe_await(handler(request, exc)))
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    async def _render_unhandled(self, request: Request, exc: Exception) -> Response:
        handler = self._lookup_exception_handler(type(exc))
        if handler is not None:
            return coerce_response(await _maybe_await(handler(request, exc)))
        logger.exception("Unhandled error for %s %s", request.method, request.path)
        if self.debug:
            return PlainTextResponse(traceback.format_exc(), status_code=500)
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)

    async def _handle_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle a WebSocket connection."""
        ws = WebSocket(scope, receive, send)
        scope["app"] = self
        result = self.router.find_websocket(ws.path)
        if result is None:
            # Reject — no handler found
            await receive()  # consume connect
            await send({"type": "websocket.close", "code": 4004, "reason": "Not Found"})
            return
        endpoint, params = result
        ws.path_params = params
        try:
            await endpoint(ws)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket error on %s", ws.path)
            try:
                await ws.close(code=1011)
            except Exception:
                pass

    def __repr__(self) -> str:
        return f"<Shakti title={self.title!r} routes={len(self.router.routes)}>"


class _AppState:
    """Attribute bag for application-level state."""

    def __init__(self) -> None:
        object.__setattr__(self, "_state", {})

    def __setattr__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: str) -> Any:
        try:
            return self._state[key]
        except KeyError as exc:
            raise AttributeError(f"App state has no attribute {key!r}") from exc
