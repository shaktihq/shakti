# Deployment

Shakti is a plain ASGI app (`shakti.Shakti` implements the ASGI interface directly) — anything that runs an ASGI app can run Shakti. `shakti run` is a dev convenience wrapper around `uvicorn`; in production, run uvicorn (or another ASGI server) yourself with proper process management.

## Running in production

```bash
pip install "shakti-framework[server]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Don't use `--reload` in production — it's a dev-only file watcher. For multiple workers, put a process manager in front (systemd, Docker + an orchestrator, or a tool like `gunicorn -k uvicorn.workers.UvicornWorker`) rather than relying on uvicorn's own `--workers` flag alone for resilience — it restarts workers but doesn't supervise the whole process the way systemd/Docker does.

## Configuration profile

Set `SHAKTI_ENV=production` so `Config` picks up `config/settings.production.yaml` (deep-merged over `config/settings.yaml`) — see [Configuration](core/config.md#profiles). `shakti new` scaffolds a production profile with `app.debug: false` and `database.url: ${DATABASE_URL}` by default:

```yaml
# config/settings.production.yaml
app:
  debug: false
database:
  url: ${DATABASE_URL}
```

Always run with `debug=False` in production — `debug=True` returns full tracebacks in `500` responses (see [Request & Response: error handling](core/request-response.md#error-handling)), which leaks internals to clients.

```bash
export SHAKTI_ENV=production
export DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
export SECRET_KEY=...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Migrations before rollout

Run `shakti migrate` as a separate deploy step before traffic hits new workers, not from application startup code — see [Migrations](orm/migrations.md).

## Health checks

Wire up [`Monitor`](monitoring.md) and point your orchestrator's probes at it:

```python
from shakti.monitoring import Monitor
monitor = Monitor()
monitor.init_app(app)
```

| Probe | Endpoint |
|---|---|
| Liveness | `GET /monitor/health/live` |
| Readiness | `GET /monitor/health/ready` |

Add your own checks (DB connectivity, AI provider reachability) with `@monitor.health_check(name)` so readiness actually reflects whether the app can serve traffic.

## CORS and rate limiting

If the app is called from a browser on a different origin, add `CORSMiddleware` explicitly — set `allow_origins` to your real frontend origin(s) in production rather than leaving the `["*"]` default. Consider `RateLimitMiddleware` for public endpoints. See [Middleware](core/middleware.md).

## Static assets

`app.static()` serves files with proper `Cache-Control` — `immutable` for content-hashed filenames, short-lived otherwise — and always returns a genuine `404` for missing files (never a silent `200` fallback). See [Routing: static files](core/routing.md#static-files). For high-traffic public asset serving, still put a CDN or reverse proxy (nginx, Cloudflare, etc.) in front — `app.static()` is in-process file I/O, fine for internal tools and moderate traffic, not a CDN replacement.

## Secrets

Use `config.secret(key)` rather than `config.get(key)` for credentials — its `repr()` never exposes the value, so a stray `print(config)` or log line doesn't leak it. Supports both environment variables and Docker/Kubernetes-style `_FILE`-suffixed secret files. See [Configuration: secrets](core/config.md#secrets).

## Background jobs and schedulers

`WorkflowEngine`'s queue and scheduler are in-process — running multiple workers means multiple independent schedulers, so a `@workflows.every(...)` job will fire once per worker process, not once cluster-wide. If that matters for your job (e.g. it's not idempotent), either pin scheduled/background work to a single dedicated process, or move to an external broker. See [Workflows: scope and limits](workflows.md#scope-and-limits).

## Checklist

- `SHAKTI_ENV=production`, `app.debug: false`
- Real database URL via `DATABASE_URL` (not SQLite, for anything concurrent)
- Migrations applied before the new version receives traffic
- `CORSMiddleware` origins locked down to real frontend domain(s)
- Liveness/readiness probes wired to your orchestrator
- Secrets via `config.secret()` / environment / secret files, never committed to `config/settings.yaml`
- A process manager or orchestrator restarting workers, not `--reload`
