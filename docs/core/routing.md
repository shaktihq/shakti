---
description: Routing in Shakti Python Framework — typed path parameters, route converters, middleware groups, WebSocket routes, and static file serving.
---

# Routing

Routes are registered with decorators on the app (or on a `Router` you mount later). Handlers can be plain functions returning dicts, strings, `Response` objects, or `(body, status_code)` tuples — see [Request & Response](request-response.md).

```python
@app.get("/hello/{name}")
async def hello(name: str) -> dict:
    return {"message": f"Hello, {name}!"}
```

`app.get`, `.post`, `.put`, `.patch`, `.delete`, and `.options` all exist. `GET` routes automatically also answer `HEAD` requests.

## Path parameters

Path segments in `{curly braces}` are extracted and converted before your handler runs. Add `:type` to pick a converter:

| Converter | Regex | Python type |
|---|---|---|
| `str` (default) | `[^/]+` | `str` |
| `int` | `[0-9]+` | `int` |
| `float` | `[0-9]+(?:\.[0-9]+)?` | `float` |
| `uuid` | UUID format | `uuid.UUID` |
| `slug` | `[a-zA-Z0-9_-]+` | `str` |
| `path` | `.+` | `str` (matches `/`, useful for catch-alls) |

```python
@app.get("/posts/{post_id:int}")
async def get_post(post_id: int) -> dict:
    return {"id": post_id}

@app.get("/files/{filepath:path}")
async def get_file(filepath: str) -> dict:
    return {"path": filepath}
```

If a segment fails to convert (e.g. `/posts/abc` against `{post_id:int}`), the route doesn't match — Shakti falls through to the next route, or returns `404`/`405` as usual.

## How matching works

Routes are tried in registration order. For a given path:

- If a route's pattern matches **and** the method matches → it runs.
- If the pattern matches but the method doesn't → the framework collects all allowed methods across matching routes and raises `405` with an `Allow` header.
- If nothing matches at all → `404`.

## Handler parameters (dependency injection)

Shakti inspects each handler's signature and fills parameters automatically — see [Dependency Injection](di.md) for the full resolution order. In short: path params bind by name, `request: Request` binds the current request, a parameter named `body` gets the parsed JSON body, and query params bind by name too.

```python
@app.get("/search")
async def search(q: str, limit: int = 20) -> dict:
    # q comes from ?q=..., limit from ?limit=... (or defaults to 20)
    return {"query": q, "limit": limit}

@app.post("/posts")
async def create_post(body: dict) -> dict:
    return {"title": body["title"]}
```

## Grouping routes with `Router`

Use `Router` to group related routes under a shared prefix and middleware, then mount it on the app:

```python
from shakti import Router

posts = Router(prefix="/posts")

@posts.get("/")
async def list_posts() -> list:
    return []

@posts.get("/{post_id:int}")
async def get_post(post_id: int) -> dict:
    return {"id": post_id}

app.include_router(posts)
```

`include_router` also accepts an extra `prefix` at mount time, and composes group middleware outermost-first (the router's own middleware, then the included router's).

## WebSocket routes

```python
@app.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    async for msg in ws.iter_json():
        await ws.send_json({"echo": msg})
```

See [WebSockets](../websockets.md) for the full API.

## Static files

`app.static()` serves a directory of files under a path prefix, with production-sane cache headers out of the box:

```python
app.static("/assets", "dist/assets")
```

- A missing file always returns a real `404` — it's never masked behind a `200` HTML fallback.
- Filenames that look content-hashed (e.g. `app.9f8c1a2b.js`) get `Cache-Control: public, max-age=31536000, immutable`.
- Everything else gets a short-lived `Cache-Control: public, max-age=3600`.
- Pass `html=True` to serve `index.html` for extensionless paths (SPA-style fallback) — this only kicks in for paths without a dot, so a genuinely missing asset (`app.js`) still 404s instead of silently returning HTML.

```python
app.static("/", "dist", html=True)  # SPA served from dist/, real 404s for missing assets
```

### Manifest-aware caching

The filename-pattern check above is a guess — good enough for typical builds, but a mutable file that happens to have a hash-like name would be wrongly cached forever. Pass `immutable_manifest` to make it exact instead: it becomes the sole source of truth for which files count as immutable.

```python
app.static("/assets", "dist/assets", immutable_manifest="dist/manifest.json")
```

Accepts:

- a path (or `Path`) to a JSON manifest file,
- a dict — either Vite's shape (`{"src/main.ts": {"file": "app.4889e19a.js", "css": [...], "assets": [...]}}`) or a flat Webpack-style `{name: hashed_name}` map, auto-detected per entry,
- or a plain iterable of hashed filenames you've already computed yourself.

Only basenames are compared, so it doesn't matter whether the manifest's paths are nested differently from how you're serving them. Anything not listed in the manifest — including a file whose name coincidentally matches the fingerprint pattern — gets the regular short-lived `max_age` instead of `immutable`.

This also does the right thing across a rolling deployment: an old build's still-on-disk hashed file won't be in the *new* manifest, so it falls back to short-lived caching rather than immutable. That's a small efficiency cost for the outgoing build's assets, not a correctness issue — mixed-version clients still get the right bytes.
