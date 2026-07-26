from shakti import Shakti, Router
from shakti.testing import TestClient

app = Shakti(debug=False)


@app.get("/")
async def index() -> dict:
    return {"ok": True}


@app.get("/users/{user_id:int}")
async def get_user(user_id: int) -> dict:
    return {"user_id": user_id, "type": type(user_id).__name__}


@app.get("/files/{filepath:path}")
async def files(filepath: str) -> dict:
    return {"path": filepath}


@app.post("/echo")
async def echo(body: dict) -> dict:
    return {"received": body}


v1 = Router(prefix="/v1")


@v1.get("/ping")
async def ping() -> str:
    return "pong"


api = Router(prefix="/api")


@api.get("/items")
async def items() -> list:
    return [1, 2, 3]


api.include_router(v1)
app.include_router(api)

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_typed_path_param() -> None:
    response = client.get("/users/42")
    assert response.json() == {"user_id": 42, "type": "int"}


def test_typed_path_param_rejects_non_int() -> None:
    assert client.get("/users/abc").status_code == 404


def test_path_converter() -> None:
    response = client.get("/files/reports/2026/q1.pdf")
    assert response.json() == {"path": "reports/2026/q1.pdf"}


def test_nested_router_prefixes() -> None:
    assert client.get("/api/items").json() == [1, 2, 3]
    response = client.get("/api/v1/ping")
    assert response.text == "pong"
    assert response.headers.get("content-type").startswith("text/plain")


def test_404() -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_405_with_allow_header() -> None:
    response = client.post("/")
    assert response.status_code == 405
    assert "GET" in response.headers.get("allow")


def test_json_body_binding() -> None:
    response = client.post("/echo", json={"a": 1})
    assert response.json() == {"received": {"a": 1}}


def test_malformed_json_body() -> None:
    response = client.post(
        "/echo", content="{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
