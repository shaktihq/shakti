import pytest

from shakti import JSONResponse, SecurityHeadersMiddleware, Shakti
from shakti.http.request import Request
from shakti.testing import TestClient


def make_app(**kwargs) -> Shakti:
    app = Shakti(debug=False)
    app.add_middleware(SecurityHeadersMiddleware, **kwargs)

    @app.get("/")
    async def index() -> dict:
        return {"ok": True}

    return app


def test_default_headers_present() -> None:
    client = TestClient(make_app())
    response = client.get("/")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_hsts_omitted_over_plain_http() -> None:
    # TestClient issues requests with scheme "http" — HSTS must not be sent
    client = TestClient(make_app())
    response = client.get("/")
    assert response.headers.get("strict-transport-security") is None


@pytest.mark.asyncio
async def test_hsts_present_over_https() -> None:
    # TestClient always uses scheme "http", so drive dispatch() directly
    # with an https scope to exercise the HSTS branch.
    scope = {"type": "http", "method": "GET", "path": "/", "scheme": "https", "headers": []}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive)
    middleware = SecurityHeadersMiddleware(hsts_include_subdomains=True, hsts_preload=True)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)
    value = response.headers.get("strict-transport-security")
    assert value == "max-age=31536000; includeSubDomains; preload"


def test_csp_and_permissions_policy_opt_in() -> None:
    client = TestClient(
        make_app(
            content_security_policy="default-src 'self'",
            permissions_policy="geolocation=()",
        )
    )
    response = client.get("/")
    assert response.headers.get("content-security-policy") == "default-src 'self'"
    assert response.headers.get("permissions-policy") == "geolocation=()"


def test_headers_disabled_when_none() -> None:
    client = TestClient(
        make_app(frame_options=None, referrer_policy=None, content_type_options=False, hsts=False)
    )
    response = client.get("/")
    assert response.headers.get("x-frame-options") is None
    assert response.headers.get("x-content-type-options") is None
    assert response.headers.get("referrer-policy") is None
    assert response.headers.get("strict-transport-security") is None


def test_does_not_override_handler_set_header() -> None:
    app = Shakti(debug=False)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/custom")
    async def custom():
        response = JSONResponse({"ok": True})
        response.headers.set("x-frame-options", "SAMEORIGIN")
        return response

    client = TestClient(app)
    response = client.get("/custom")
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"
