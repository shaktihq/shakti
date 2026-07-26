from shakti import Shakti, Router
from shakti.middleware import BaseHTTPMiddleware, CORSMiddleware
from shakti.testing import TestClient

events: list[str] = []


class TrackMiddleware(BaseHTTPMiddleware):
    def __init__(self, label: str) -> None:
        self.label = label

    async def dispatch(self, request, call_next):
        events.append(f"{self.label}:in")
        response = await call_next(request)
        events.append(f"{self.label}:out")
        response.headers.append("x-trace", self.label)
        return response


app = Shakti(debug=False)
app.add_middleware(TrackMiddleware, label="outer")

traced = Router(prefix="/traced", middleware=[TrackMiddleware("group")])


@traced.get("/ping")
async def traced_ping() -> dict:
    return {"pong": True}


app.include_router(traced)


@app.get("/plain")
async def plain() -> dict:
    return {"plain": True}


client = TestClient(app)


def test_middleware_order() -> None:
    events.clear()
    response = client.get("/traced/ping")
    assert response.status_code == 200
    assert events == ["outer:in", "group:in", "group:out", "outer:out"]
    assert response.headers.getlist("x-trace") == ["group", "outer"]


def test_group_middleware_is_scoped() -> None:
    events.clear()
    client.get("/plain")
    assert events == ["outer:in", "outer:out"]


cors_app = Shakti(debug=False)
cors_app.add_middleware(CORSMiddleware, allow_origins=["https://ok.dev"])


@cors_app.get("/data")
async def data() -> dict:
    return {"n": 1}


cors_client = TestClient(cors_app)


def test_cors_preflight() -> None:
    response = cors_client.options(
        "/data",
        headers={
            "origin": "https://ok.dev",
            "access-control-request-method": "GET",
        },
    )
    assert response.status_code == 204
    assert response.headers.get("access-control-allow-origin") == "https://ok.dev"
    assert "GET" in response.headers.get("access-control-allow-methods")


def test_cors_simple_request() -> None:
    response = cors_client.get("/data", headers={"origin": "https://ok.dev"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://ok.dev"


def test_cors_disallowed_origin_gets_no_headers() -> None:
    response = cors_client.get("/data", headers={"origin": "https://evil.dev"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
