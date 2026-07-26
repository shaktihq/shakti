"""Shakti — an AI-first, async Python web framework.

Flask simplicity, FastAPI performance, Django batteries.
"""

from shakti.__about__ import __version__
from shakti.admin import Admin
from shakti.ai import AI, SSEResponse
from shakti.application import Shakti, coerce_response
from shakti.auth import Auth
from shakti.auth.models import APIKey, User
from shakti.config.secrets import Secret
from shakti.config.settings import Config
from shakti.di import Container, Depends
from shakti.docs import DocumentAI
from shakti.exceptions import ConfigError, HTTPException, RouteError, ShaktiError
from shakti.http.request import Request
from shakti.http.response import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from shakti.monitoring import Monitor
from shakti.routing.route import Route
from shakti.routing.router import Router
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
    "Shakti",
    "ShaktiError",
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
from shakti.openapi import OpenAPI
from shakti.upload import UploadFile
