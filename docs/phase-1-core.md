# Phase 1 — Core Framework

## Application

```python
from shakti import Shakti

app = Shakti(title="My API", debug=False)
```

`Shakti` is a plain ASGI application. Run it with any ASGI server:

```bash
shakti run app.main:app --reload
# equivalent to: uvicorn app.main:app --reload
```

### Lifecycle

```python
@app.on_startup
async def connect(): ...

@app.on_shutdown
async def disconnect(): ...
```

Hooks run via the ASGI lifespan protocol; `app.startup()` / `app.shutdown()`
are also awaitable directly (the test client uses them).

## Routing

Decorators exist for `get`, `post`, `put`, `patch`, `delete`, `options`,
`head`, plus a generic `route(path, methods=[...])`.

### Path converters

`{name}` (str, default), `{id:int}`, `{price:float}`, `{key:uuid}`,
`{slug:slug}`, `{filepath:path}`. A converter that fails to cast means the
route does not match.

### Route groups

```python
from shakti import Router

v1 = Router(prefix="/v1")
api = Router(prefix="/api", middleware=[AuthMiddleware()])
api.include_router(v1)
app.include_router(api)          # optional extra prefix: prefix="/mounted"
```

Group middleware composes outermost (parent) to innermost (child) and only
applies to routes in that group.

### Return values

| Handler returns | Response |
|---|---|
| `Response` subclass | used as-is |
| `dict` / `list` | `JSONResponse` |
| `str` | `PlainTextResponse` |
| `None` | 204 No Content |
| `(body, status)` tuple | body coerced, status applied |
| `bytes` | `application/octet-stream` |

### Errors

Raise `HTTPException(status, detail, headers)` anywhere. Unknown paths get
404; known paths with wrong methods get 405 with an `Allow` header.
Register custom handlers per exception type:

```python
@app.exception_handler(KeyError)
async def handle(request, exc):
    return {"detail": "missing key"}, 400
```

Unhandled exceptions return a JSON 500 (full traceback in the body only when
`debug=True`).

## Request & Response

`Request` exposes `method`, `path`, `headers`, `query_params`, `cookies`,
`path_params`, `client`, `state`, and async `body()`, `json()`, `form()`.

Responses: `Response`, `JSONResponse`, `HTMLResponse`, `PlainTextResponse`,
`RedirectResponse`, with `set_cookie` / `delete_cookie`.

## Dependency injection

Parameter binding order for handler arguments:

1. `Depends(fn)` default — resolved recursively, cached per request
2. `Request` annotation — the current request
3. Path params — cast to the annotated type
4. Container-registered annotation — resolved service
5. `body` parameter name — parsed JSON body
6. Query params — cast to the annotated type (bool accepts `1/true/yes/on`)
7. Parameter default
8. Otherwise — 422

```python
app.container.register(Database)                 # lazy singleton
app.container.register(Cache, singleton=False)   # new instance each resolve
app.container.register_instance(Settings, settings)
```

`Config` and the `Shakti` app itself are pre-registered.

## Middleware

Subclass `BaseHTTPMiddleware` and override `dispatch(request, call_next)`.
App-level middleware wraps routing itself, so it also sees 404/405 and error
responses. Built-ins: `CORSMiddleware`, `RequestLoggingMiddleware`.

## Configuration

```python
from shakti.config import Config
config = Config()   # reads config/ + .env, profile from SHADOWFORGE_ENV
```

Priority: `os.environ` → `.env` → `settings.<profile>.yaml` →
`settings.yaml` → `defaults`. Dotted keys map to env vars with double
underscores (`database.url` → `DATABASE__URL`). String values support
`${VAR}` / `${VAR:default}` interpolation. `config.secret("db_password")`
supports Docker-style `DB_PASSWORD_FILE` indirection and returns a masked
`Secret`.

## Testing

```python
from shakti.testing import TestClient
client = TestClient(app)
client.get("/users/1?verbose=true")
client.post("/users", json={"name": "x"})
with TestClient(app) as client:   # runs startup/shutdown hooks
    ...
```

## CLI

```
shakti new <name> [--directory DIR]
shakti run [module:app] [--host] [--port] [--reload] [--workers]
shakti version
```
