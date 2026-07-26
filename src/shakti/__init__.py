"""Shakti — an AI-first, async Python web framework.

Flask simplicity, FastAPI performance, Django batteries.
"""

from shakti.__about__ import __version__
from shakti.application import Shakti, coerce_response
from shakti.config.secrets import Secret
from shakti.config.settings import Config
from shakti.di import Container, Depends
from shakti.exceptions import ConfigError, HTTPException, ShaktiError, RouteError
from shakti.http.request import Request
from shakti.http.response import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from shakti.admin import Admin
from shakti.ai import AI, SSEResponse
from shakti.docs import DocumentAI
from shakti.workflows import WorkflowEngine
from shakti.monitoring import Monitor
from shakti.auth import Auth
from shakti.auth.models import APIKey, User
from shakti.routing.route import Route
from shakti.websocket import WebSocket, WebSocketDisconnect
from shakti.routing.router import Router

__all__ = [
    "Config",
    "ConfigError",
    "Container",
    "Depends",
    "HTMLResponse",
    "HTTPException",
    "JSONResponse",
    "PlainTextResponse",
    "Shakti",
    "ShaktiError",
    "RedirectResponse",
    "Request",
    "Response",
    "Route",
    "RouteError",
    "WebSocket",
    "WebSocketDisconnect",
    "Router",
    "Secret",
    "AI",
    "DocumentAI",
    "Monitor",
    "WorkflowEngine",
    "Admin",
    "SSEResponse",
    "APIKey",
    "Auth",
    "User",
    "__version__",
    "coerce_response",
]
