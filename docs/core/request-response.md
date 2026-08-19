---
description: Request and Response objects in Shakti Python Framework — headers, query params, JSON bodies, cookies, and error handling.
---

# Request & Response

## Request

Every handler can take a `request: Request` parameter (or rely on [dependency injection](di.md) to supply it by name). It's a thin, lazily-evaluated wrapper over the ASGI scope:

```python
@app.post("/webhook")
async def webhook(request: Request) -> dict:
    print(request.method, request.path, request.client)
    body = await request.json()
    return {"received": body}
```

Key attributes and methods:

| | |
|---|---|
| `request.method` | `"GET"`, `"POST"`, ... (uppercased) |
| `request.path` | the request path |
| `request.headers` | case-insensitive `Headers` — `.get(key, default)`, `.getlist(key)` |
| `request.query_params` | `.get(key, default)`, multi-value aware |
| `request.cookies` | `dict[str, str]` parsed from the `Cookie` header |
| `request.path_params` | dict of converted path parameters for this route |
| `request.client` | `(host, port)` tuple or `None` |
| `request.content_type` | the `Content-Type` header, without parameters |
| `request.state` | a free-form attribute bag for passing data between middleware and handlers |
| `await request.body()` | raw request body bytes (cached after first read) |
| `await request.json()` | parsed JSON body; `400` if empty or malformed |
| `await request.form()` | parsed `application/x-www-form-urlencoded` body |
| `await request.files()` | parsed `multipart/form-data` → `{field: UploadFile \| str}` |

## Response

Handlers don't have to return a `Response` explicitly — return values are coerced automatically:

| Return value | Becomes |
|---|---|
| `None` | `204 No Content` |
| `dict` / `list` | `JSONResponse` |
| `str` | `PlainTextResponse` |
| `bytes` / `bytearray` | `application/octet-stream` |
| `(value, status_code)` tuple | `value` coerced as above, with that status code |
| a `Response` instance | returned as-is |

```python
@app.get("/teapot")
async def teapot() -> tuple:
    return {"error": "I'm a teapot"}, 418
```

### Response classes

`Response`, `JSONResponse`, `HTMLResponse`, `PlainTextResponse`, `RedirectResponse`, and `FileResponse` are all available from `shakti`:

```python
from shakti import JSONResponse, RedirectResponse

@app.get("/login")
async def login() -> RedirectResponse:
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/data")
async def data() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.set_cookie("session", "abc123", httponly=True, secure=True, samesite="strict")
    return response
```

`FileResponse` streams a file from disk with `Content-Length`, `Last-Modified`, and `ETag` set automatically — it's what `app.static()` uses under the hood (see [Routing](routing.md#static-files)).

### Headers and cookies

```python
response.headers["X-Custom"] = "value"
response.set_cookie("token", value, max_age=3600, path="/", secure=True, httponly=True, samesite="lax")
response.delete_cookie("token")
```

## Error handling

Raise `HTTPException` anywhere in a handler, dependency, or middleware:

```python
from shakti import HTTPException

@app.get("/posts/{post_id:int}")
async def get_post(post_id: int) -> dict:
    post = await find_post(post_id)
    if post is None:
        raise HTTPException(404, "Post not found")
    return post
```

It's converted into `{"detail": "Post not found"}` with the given status code. Unhandled non-`HTTPException` errors become a generic `500 {"detail": "Internal Server Error"}` (or a traceback if `debug=True`) — the real exception is always logged either way, so nothing gets silently swallowed.

### Custom exception handlers

```python
@app.exception_handler(KeyError)
async def handle_key_error(request: Request, exc: KeyError) -> tuple:
    return {"detail": f"Missing key: {exc}"}, 400
```

Handlers are looked up by walking the exception's MRO, so registering a handler for a base class also covers its subclasses. The handler's return value goes through the same coercion rules as a normal endpoint.
