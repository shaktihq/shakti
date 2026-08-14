# Middleware

Middleware wraps request handling to add cross-cutting behavior — logging, CORS, rate limiting, auth checks — without touching individual handlers.

## Writing middleware

Subclass `BaseHTTPMiddleware` and override `dispatch`:

```python
from shakti import Request, Response
from shakti.middleware.base import BaseHTTPMiddleware, CallNext

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        import time
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
        return response
```

Call `await call_next(request)` to continue to the next middleware (or the handler itself); skip it to short-circuit and return your own response early.

## Registering middleware

```python
app.add_middleware(TimingMiddleware)
```

Or pass a pre-built instance if it needs configuration you can't express as kwargs:

```python
app.add_middleware(RateLimitMiddleware(requests=100, window=60))
```

App-level middleware runs for every request. The **first middleware added runs outermost** — it sees the request first and the response last.

Routers also accept middleware scoped to just their routes:

```python
from shakti import Router

api = Router(prefix="/api", middleware=[AuthMiddleware()])
```

Group middleware composes outermost (the router) to innermost (the route's own middleware, if any).

## Built-in middleware

### `CORSMiddleware`

```python
from shakti.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
    max_age=600,
)
```

Handles preflight `OPTIONS` requests directly and adds `Access-Control-*` headers to real responses. Defaults to `allow_origins=["*"]`.

### `RateLimitMiddleware`

```python
from shakti import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, requests=100, window=60, by="ip")
```

A sliding-window limiter keyed by client IP (`by="ip"`) or by IP+route (`by="route"`). Requests over the limit get `429` with `Retry-After` and `X-RateLimit-*` headers; requests under the limit still get `X-RateLimit-Limit` / `X-RateLimit-Remaining` set. State is in-process — for multi-worker deployments, put a shared store (e.g. Redis) behind a custom middleware instead.

### `RequestLoggingMiddleware`

```python
from shakti.middleware.logging import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
```

Logs `METHOD path -> status (duration_ms)` to the `shakti.access` logger for every request, and re-raises (after logging) if the handler chain throws.

## Exception handling and middleware

Middleware runs inside the app's top-level exception handling, so unhandled exceptions raised by `call_next(request)` still get converted into proper error responses after your middleware sees them (or propagates them) — see [Request & Response](request-response.md#error-handling).
