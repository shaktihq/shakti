---
description: Middleware in Shakti Python Framework — CORS, rate limiting, security headers, and request logging, plus how to write your own.
---

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

### `SecurityHeadersMiddleware`

```python
from shakti import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
```

Adds common security-related response headers, on by default with conservative values:

| Header | Default |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` — only sent when the request scheme is `https` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | not set (opt-in — app-specific) |
| `Permissions-Policy` | not set (opt-in) |

Every option can be tuned or disabled:

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_max_age=63_072_000,
    hsts_preload=True,
    content_security_policy="default-src 'self'",
    permissions_policy="geolocation=(), microphone=()",
    frame_options=None,   # omit the header entirely
)
```

It only ever sets a header if the handler hasn't already set one with the same name — so a response that needs a different value (e.g. `X-Frame-Options: SAMEORIGIN` for one embeddable page) can override it per-route without fighting the middleware.

`Strict-Transport-Security` is gated on `request.scope["scheme"] == "https"` so it's never sent to plain-HTTP local dev. If you're behind a reverse proxy that terminates TLS, make sure it (or your ASGI server's proxy-header handling, e.g. `uvicorn --proxy-headers`) sets the scope's scheme to `https` correctly — otherwise HSTS will silently never be sent.

### `RequestLoggingMiddleware`

```python
from shakti.middleware.logging import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
```

Logs `METHOD path -> status (duration_ms)` to the `shakti.access` logger for every request, and re-raises (after logging) if the handler chain throws.

## Exception handling and middleware

Middleware runs inside the app's top-level exception handling, so unhandled exceptions raised by `call_next(request)` still get converted into proper error responses after your middleware sees them (or propagates them) — see [Request & Response](request-response.md#error-handling).
