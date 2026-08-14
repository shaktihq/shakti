# Shakti


[![Docs](https://img.shields.io/badge/docs-shakti.adityabhat.in-purple)](https://shakti.adityabhat.in)
[![PyPI](https://img.shields.io/pypi/v/shakti-framework)](https://pypi.org/project/shakti-framework/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/shaktihq/shakti/actions/workflows/tests.yml/badge.svg)](https://github.com/shaktihq/shakti/actions)

📖 **Docs:** https://shakti.adityabhat.in

**An AI-first, async Python web framework.**

> Born in India. Built for the world.

```bash
pip install "shakti-framework[all]"
pip install shakti-framework
```

[![PyPI](https://img.shields.io/pypi/v/shakti-framework)](https://pypi.org/project/shakti-framework/)
[![Python](https://img.shields.io/pypi/pyversions/shakti-framework)](https://pypi.org/project/shakti-framework/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/shaktihq/shakti/actions/workflows/tests.yml/badge.svg)](https://github.com/shaktihq/shakti/actions)

---

## What is Shakti?

Shakti is a modern Python web framework designed for the AI era.
It gives you everything you need to build production-ready APIs
— routing, database, auth, AI, background jobs, monitoring —
all in a single install, zero configuration.

---

## Features

### ⚡ Core
- Fully async ASGI — built for speed
- Typed routing with path converters
- Middleware system (CORS, logging, rate limiting)
- Dependency injection
- Layered config (`.env` + YAML + environment variables)
- Built-in test client

### 🗄️ Database
- Async SQLAlchemy ORM
- Auto migrations with Alembic
- Repository pattern (get, filter, create, update, delete)
- Code generation — scaffold models and CRUD in one command

### 🔐 Auth
- JWT access + refresh tokens
- Role-based access control (RBAC)
- API key authentication
- Password hashing (bcrypt)
- Ready-to-use login, register, logout endpoints

### 🤖 AI
- Built-in Claude (Anthropic) and OpenAI support
- Chat, completion, and streaming
- RAG (Retrieval-Augmented Generation)
- AI agents with tool calling
- Prompt templates (summarize, translate, extract, review)

### 🖥️ Admin Panel
- Auto-generated admin UI for any model
- Dark mode and light mode
- Search, pagination, CSV export
- Activity log
- No extra setup needed

### 🔌 WebSockets
- Real-time connections
- JSON and text messaging
- Path parameters
- AI streaming over WebSocket

### 📄 Document AI
- PDF text extraction
- Image OCR via Claude Vision
- Document Q&A
- Structured data extraction
- Document classification and summarization

### ⚙️ Background Jobs
- Async job queue
- Automatic retry with exponential backoff
- Interval scheduling (every X minutes/hours/days)
- Job status tracking

### 📊 Monitoring
- Live dashboard at `/monitor/`
- Health checks (liveness + readiness probes)
- Request metrics (avg, p95, p99 response times)
- CPU, memory, disk usage
- Per-endpoint analytics
- Custom health check hooks

### 🛠️ Developer Tools
- Rate limiting middleware
- Email sending (SMTP)
- Cache (in-memory + Redis)
- File uploads (multipart)
- OpenAPI + Swagger UI at `/docs`
- ReDoc at `/redoc`

---

## Quick Start

```bash
pip install "shakti-framework[all]"
shakti new myapp
cd myapp
shakti run --reload
```

Open `http://127.0.0.1:8000` — your app is running.

---

## 60-Second Example

```python
from shakti import Shakti, Depends
from shakti.config import Config
from shakti.orm import Database, Repository
from shakti.auth import Auth
from shakti.auth.models import User
from shakti.ai import AI
from shakti.admin import Admin
from shakti.monitoring import Monitor
from shakti.workflows import WorkflowEngine
from shakti.websocket import WebSocket

config = Config()
app = Shakti(title="My App", config=config)

db = Database(config.require("database.url"))
db.init_app(app)

auth = Auth(db, secret_key=config.require("auth.secret_key"))
auth.init_app(app)

ai = AI(config)
ai.init_app(app)

admin = Admin(db, auth, title="My Admin")
admin.register(User)
admin.init_app(app)

monitor = Monitor()
monitor.init_app(app)

workflows = WorkflowEngine()
workflows.init_app(app)


@app.get("/")
async def index() -> dict:
    return {"framework": "Shakti", "status": "running"}


@app.get("/me")
async def me(user: User = Depends(auth.get_current_user())) -> dict:
    return user.to_dict()


@app.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    async for msg in ws.iter_json():
        reply = await ai.chat(msg["text"])
        await ws.send_json({"reply": reply})
```

---

## Code Generation

Scaffold a full API with one command:

```bash
# Generate model
shakti generate model Post title:str body:text views:int

# Generate model + full CRUD endpoints
shakti generate api Post title:str body:text views:int

# Run migrations
shakti makemigrations "add posts"
shakti migrate
```

That's it. You now have:
- `POST /posts` — create
- `GET /posts` — list all
- `GET /posts/{id}` — get one
- `PUT /posts/{id}` — update
- `DELETE /posts/{id}` — delete

---

## CLI Reference

```bash
shakti new myapp                              # scaffold project
shakti run --reload                           # start dev server
shakti generate model Post title:str          # generate model
shakti generate crud Post                     # generate CRUD
shakti generate api Post title:str body:text  # model + CRUD
shakti makemigrations "message"               # create migration
shakti migrate                                # apply migrations
shakti db history                             # migration history
shakti db current                             # current revision
shakti version                                # show version
```

---

## Configuration

```yaml
# config/settings.yaml
app:
  name: myapp
  debug: true

database:
  url: sqlite+aiosqlite:///./myapp.db

auth:
  secret_key: ${SECRET_KEY}
  access_token_expire_minutes: 30

ai:
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: ${ANTHROPIC_API_KEY}
  system_prompt: "You are a helpful assistant."

mail:
  host: smtp.gmail.com
  port: 587
  username: you@gmail.com
  password: ${MAIL_PASSWORD}
```

```bash
# .env
SHAKTI_ENV=development
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-key
```

---

## Install Options

```bash
pip install shakti-framework                    # core only
pip install "shakti-framework[server]"          # + uvicorn
pip install "shakti-framework[orm]"             # + SQLAlchemy + Alembic
pip install "shakti-framework[auth]"            # + JWT + bcrypt
pip install "shakti-framework[ai]"              # + Claude + OpenAI
pip install "shakti-framework[monitoring]"      # + system metrics
pip install "shakti-framework[all]"             # everything
```

---

## Modules

| Module | Import | What it does |
|--------|--------|--------------|
| Core | `from shakti import Shakti` | Routing, middleware, DI, config |
| ORM | `from shakti.orm import Database` | SQLAlchemy async + migrations |
| Auth | `from shakti.auth import Auth` | JWT, RBAC, API keys |
| AI | `from shakti.ai import AI` | Claude/OpenAI, RAG, agents |
| Admin | `from shakti.admin import Admin` | Auto-generated admin panel |
| WebSocket | `from shakti.websocket import WebSocket` | Real-time connections |
| Document AI | `from shakti.docs import DocumentAI` | PDF, OCR, document Q&A |
| Workflows | `from shakti.workflows import WorkflowEngine` | Background jobs |
| Monitoring | `from shakti.monitoring import Monitor` | Health checks, metrics |
| Cache | `from shakti.cache import Cache` | Memory + Redis caching |
| Mailer | `from shakti.mailer import Mailer` | Send emails |
| OpenAPI | `from shakti.openapi import OpenAPI` | Swagger UI + ReDoc |
| Rate Limit | `from shakti.middleware import RateLimitMiddleware` | Request rate limiting |

---

## Auth Endpoints

Auto-registered when you call `auth.init_app(app)`:

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, get tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Current user info |

---

## AI Endpoints

Auto-registered when you call `ai.init_app(app)`:

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/ai/chat` | Single or multi-turn chat |
| POST | `/ai/complete` | Chat with token counts |
| POST | `/ai/stream` | Server-sent events streaming |
| POST | `/ai/rag/add` | Add document to RAG store |
| POST | `/ai/rag/query` | Ask question with context |
| GET | `/ai/info` | Provider and model info |

---

## License

MIT © Aditya Bhat — Born in India 🇮🇳
