# Monitoring

Built-in health checks, metrics, and a live dashboard.

## Setup

```python
from shakti.monitoring import Monitor

monitor = Monitor(title="My App Monitor")
monitor.init_app(app)
```

Visit `http://localhost:8000/monitor/` — auto-refreshes every 10 seconds.

## Custom health checks

```python
@monitor.health_check("database")
async def check_db() -> str:
    async with db.session() as session:
        await session.execute(text("SELECT 1"))
    return "connected"

@monitor.health_check("ai")
async def check_ai() -> str:
    # ping your AI provider
    return "ok"
```

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /monitor/` | Live dashboard |
| `GET /monitor/health` | Basic health |
| `GET /monitor/health/live` | Kubernetes liveness probe |
| `GET /monitor/health/ready` | Kubernetes readiness probe |
| `GET /monitor/health/full` | Full health + system info |
| `GET /monitor/metrics` | JSON metrics |
| `GET /monitor/metrics/endpoints` | Per-endpoint stats |
| `GET /monitor/metrics/requests` | Recent request log |

## Dashboard shows

- Uptime, total requests, avg/p95 response time, error rate
- CPU, memory, disk usage (progress bars)
- Health check statuses
- Per-endpoint request counts and response times
- Recent requests log with status codes
