"""Shakti — an AI-first, async Python web framework.

Flask simplicity, FastAPI performance, Django batteries.
"""

import importlib

from shakti.__about__ import __version__
from shakti.ai import AI, SSEResponse
from shakti.application import Shakti, coerce_response
from shakti.config.secrets import Secret
from shakti.config.settings import Config
from shakti.di import Container, Depends
from shakti.docs import DocumentAI
from shakti.exceptions import ConfigError, HTTPException, RouteError, ShaktiError
from shakti.http.request import Request
from shakti.http.response import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from shakti.monitoring import Monitor
from shakti.routing.route import Route
from shakti.routing.router import Router
from shakti.staticfiles import StaticFiles
from shakti.websocket import WebSocket, WebSocketDisconnect
from shakti.workflows import WorkflowEngine

__all__ = [
    "AI",
    "APIKey",
    "Admin",
    "Auth",
    "Cache",
    "Config",
    "ConfigError",
    "Container",
    "Depends",
    "DocumentAI",
    "FileResponse",
    "HTMLResponse",
    "HTTPException",
    "JSONResponse",
    "Mailer",
    "Monitor",
    "OpenAPI",
    "PlainTextResponse",
    "RateLimitMiddleware",
    "RedirectResponse",
    "Request",
    "Response",
    "Route",
    "RouteError",
    "Router",
    "SSEResponse",
    "Secret",
    "SecurityHeadersMiddleware",
    "Shakti",
    "ShaktiError",
    "StaticFiles",
    "UploadFile",
    "User",
    "WebSocket",
    "WebSocketDisconnect",
    "WorkflowEngine",
    "__version__",
    "coerce_response",
]

from shakti.cache import Cache
from shakti.mailer import Mailer
from shakti.middleware.ratelimit import RateLimitMiddleware
from shakti.middleware.security import SecurityHeadersMiddleware
from shakti.openapi import OpenAPI
from shakti.upload import UploadFile

# Admin/Auth pull in sqlalchemy, bcrypt, and PyJWT (the ``orm``/``auth``
# extras) — import them lazily so ``import shakti`` works with only the base
# dependency (pyyaml). Accessing shakti.Admin/Auth/APIKey/User without those
# extras installed still raises ImportError, just at the point of use rather
# than for every user of the framework regardless of which features they use.
_LAZY_ATTRS = {
    "Admin": ("shakti.admin", "Admin"),
    "Auth": ("shakti.auth", "Auth"),
    "APIKey": ("shakti.auth.models", "APIKey"),
    "User": ("shakti.auth.models", "User"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(importlib.import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
