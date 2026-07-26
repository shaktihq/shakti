"""v0.2.0 feature tests."""
from __future__ import annotations

import asyncio
import base64

import pytest

from shakti import Shakti
from shakti.cache import Cache
from shakti.middleware.ratelimit import RateLimitMiddleware
from shakti.openapi import OpenAPI, generate_spec
from shakti.testing import TestClient
from shakti.upload import UploadFile, parse_multipart


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

def test_rate_limit_allows_under_limit():
    app = Shakti()
    app.add_middleware(RateLimitMiddleware, requests=5, window=60)

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    client = TestClient(app)
    for _ in range(5):
        assert client.get("/ping").status_code == 200


def test_rate_limit_blocks_over_limit():
    app = Shakti()
    app.add_middleware(RateLimitMiddleware, requests=3, window=60)

    @app.get("/limited")
    async def limited() -> dict:
        return {"ok": True}

    client = TestClient(app)
    for _ in range(3):
        client.get("/limited")
    r = client.get("/limited")
    assert r.status_code == 429
    assert "Rate limit" in r.json()["detail"]


def test_rate_limit_headers():
    app = Shakti()
    app.add_middleware(RateLimitMiddleware, requests=10, window=60)

    @app.get("/h")
    async def h() -> dict:
        return {}

    client = TestClient(app)
    r = client.get("/h")
    assert r.headers.get("x-ratelimit-limit") == "10"
    assert r.headers.get("x-ratelimit-remaining") is not None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_set_get():
    cache = Cache()
    asyncio.run(cache.set("key1", {"value": 42}, ttl=60))
    result = asyncio.run(cache.get("key1"))
    assert result == {"value": 42}


def test_cache_miss_returns_none():
    cache = Cache()
    result = asyncio.run(cache.get("nonexistent"))
    assert result is None


def test_cache_delete():
    cache = Cache()
    asyncio.run(cache.set("del_key", "hello"))
    asyncio.run(cache.delete("del_key"))
    assert asyncio.run(cache.get("del_key")) is None


def test_cache_clear():
    cache = Cache()
    asyncio.run(cache.set("a", 1))
    asyncio.run(cache.set("b", 2))
    asyncio.run(cache.clear())
    assert asyncio.run(cache.get("a")) is None


def test_cache_decorator():
    cache = Cache()
    call_count = {"n": 0}

    @cache.cached(ttl=60)
    async def expensive(x: int) -> int:
        call_count["n"] += 1
        return x * 2

    asyncio.run(expensive(5))
    asyncio.run(expensive(5))  # cached
    assert call_count["n"] == 1
    asyncio.run(expensive(6))  # different arg
    assert call_count["n"] == 2


def test_cache_exists():
    cache = Cache()
    asyncio.run(cache.set("exists_key", "yes"))
    assert asyncio.run(cache.exists("exists_key")) is True
    assert asyncio.run(cache.exists("no_key")) is False


# ---------------------------------------------------------------------------
# File Upload
# ---------------------------------------------------------------------------

def _make_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = "----TestBoundary123"
    body = b""
    for name, value in fields.items():
        body += f"------TestBoundary123\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
    for name, (filename, content, ct) in files.items():
        body += f"------TestBoundary123\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {ct}\r\n\r\n".encode()
        body += content
        body += b"\r\n"
    body += b"------TestBoundary123--\r\n"
    return body, boundary


def test_parse_multipart_text_field():
    body, boundary = _make_multipart({"username": "aditya"}, {})
    result = parse_multipart(body, boundary)
    assert result["username"] == "aditya"


def test_parse_multipart_file():
    file_content = b"Hello PDF content"
    body, boundary = _make_multipart(
        {},
        {"document": ("test.pdf", file_content, "application/pdf")}
    )
    result = parse_multipart(body, boundary)
    assert "document" in result
    upload = result["document"]
    assert isinstance(upload, UploadFile)
    assert upload.filename == "test.pdf"
    assert upload.size == len(file_content)


def test_upload_file_read():
    content = b"test content"
    f = UploadFile(filename="test.txt", content_type="text/plain", content=content)
    result = asyncio.run(f.read())
    assert result == content





# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------

def test_openapi_spec_generated():
    app = Shakti(title="Test API", version="1.0.0")

    @app.get("/users")
    async def list_users() -> list:
        return []

    @app.post("/users")
    async def create_user(body: dict) -> dict:
        return {}

    spec = generate_spec(app, "Test API", "1.0.0")
    assert spec["openapi"] == "3.0.0"
    assert spec["info"]["title"] == "Test API"
    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]
    assert "post" in spec["paths"]["/users"]


def test_swagger_ui_route():
    app = Shakti(title="My API")

    @app.get("/hello")
    async def hello() -> dict:
        return {"hello": "world"}

    openapi = OpenAPI(app, title="My API", version="1.0.0")
    openapi.init_app(app)

    client = TestClient(app)
    r = client.get("/docs")
    assert r.status_code == 200
    assert b"swagger" in r.content.lower()


def test_openapi_json_route():
    app = Shakti(title="My API")

    @app.get("/items")
    async def items() -> list:
        return []

    openapi = OpenAPI(app)
    openapi.init_app(app)

    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
    assert "/items" in data["paths"]


def test_redoc_route():
    app = Shakti()
    openapi = OpenAPI(app)
    openapi.init_app(app)

    client = TestClient(app)
    r = client.get("/redoc")
    assert r.status_code == 200
    assert b"redoc" in r.content.lower()
