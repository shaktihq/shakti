from shakti import HTTPException, JSONResponse, Shakti, RedirectResponse
from shakti.testing import TestClient

app = Shakti(debug=False)


@app.get("/none")
async def none_route() -> None:
    return None


@app.get("/text")
async def text_route() -> str:
    return "hello"


@app.get("/tuple")
async def tuple_route():
    return {"error": "teapot"}, 418


@app.get("/cookie")
async def cookie_route() -> JSONResponse:
    response = JSONResponse({"set": True})
    response.set_cookie("session", "abc", httponly=True, secure=True)
    return response


@app.get("/redirect")
async def redirect_route() -> RedirectResponse:
    return RedirectResponse("/text")


@app.get("/boom")
async def boom_route() -> None:
    raise HTTPException(400, "Bad input")


@app.get("/crash")
async def crash_route() -> None:
    raise ValueError("kaput")


@app.get("/keyerror")
async def keyerror_route() -> None:
    raise KeyError("token")


@app.exception_handler(KeyError)
async def handle_keyerror(request, exc):
    return {"detail": "missing key"}, 400


client = TestClient(app)


def test_none_becomes_204() -> None:
    response = client.get("/none")
    assert response.status_code == 204
    assert response.content == b""


def test_str_becomes_plain_text() -> None:
    response = client.get("/text")
    assert response.text == "hello"
    assert response.headers.get("content-type") == "text/plain; charset=utf-8"


def test_tuple_sets_status() -> None:
    response = client.get("/tuple")
    assert response.status_code == 418
    assert response.json() == {"error": "teapot"}


def test_set_cookie() -> None:
    response = client.get("/cookie")
    cookie = response.headers.get("set-cookie")
    assert "session=abc" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie


def test_redirect() -> None:
    response = client.get("/redirect")
    assert response.status_code == 307
    assert response.headers.get("location") == "/text"


def test_http_exception() -> None:
    response = client.get("/boom")
    assert response.status_code == 400
    assert response.json() == {"detail": "Bad input"}


def test_unhandled_error_is_500_without_leaking() -> None:
    response = client.get("/crash")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "kaput" not in response.text


def test_custom_exception_handler() -> None:
    response = client.get("/keyerror")
    assert response.status_code == 400
    assert response.json() == {"detail": "missing key"}


def test_lifespan_hooks() -> None:
    lifecycle_app = Shakti(debug=False)
    flags: list[str] = []

    @lifecycle_app.on_startup
    async def up() -> None:
        flags.append("up")

    @lifecycle_app.on_shutdown
    async def down() -> None:
        flags.append("down")

    @lifecycle_app.get("/ok")
    async def ok() -> dict:
        return {"ok": True}

    with TestClient(lifecycle_app) as lifecycle_client:
        assert lifecycle_client.get("/ok").status_code == 200
        assert flags == ["up"]
    assert flags == ["up", "down"]
