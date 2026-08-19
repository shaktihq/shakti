---
title: Shakti Python Framework — AI-First Python Web Framework
description: Shakti is an open-source AI-first Python web framework for building modern APIs, web applications, AI agents, and enterprise applications.
hide:
  - navigation
  - toc
---

<div class="hero">

<div class="hero-badge">🇮🇳 Born in India · Built for the world</div>

<h1>Shakti Python Framework</h1>

<p class="hero-subtitle">
  The AI-first Python web framework, built on async ASGI.<br>
  Everything you need to build APIs, web applications, and AI agents — one install, zero config.
</p>

<div class="cta-buttons">
  <a href="getting-started/installation/" class="cta-primary">Get Started →</a>
  <a href="https://github.com/shaktihq/shakti" class="cta-secondary">⭐ Star on GitHub</a>
</div>

<div class="install-box">
  pip install "shakti-framework[all]"
</div>

</div>

---

Shakti Python Framework is an open-source, AI-first **Python web framework** for teams who want an async foundation — routing, an async ORM, authentication, and AI integration — without stitching together a dozen separate libraries. If you've used FastAPI, Flask, or Django, Shakti's [Quick Start](getting-started/quickstart.md) will feel familiar; the [full documentation](getting-started/installation.md) covers everything from your first route to deploying an AI agent in production.

---

<div class="stats-bar">
  <div class="stat-item">
    <div class="stat-number">249</div>
    <div class="stat-label">Tests Passing</div>
  </div>
  <div class="stat-item">
    <div class="stat-number">13</div>
    <div class="stat-label">Modules</div>
  </div>
  <div class="stat-item">
    <div class="stat-number">0.2.5</div>
    <div class="stat-label">Latest Version</div>
  </div>
  <div class="stat-item">
    <div class="stat-number">MIT</div>
    <div class="stat-label">License</div>
  </div>
</div>

---

## Everything Included

<div class="feature-grid">

<div class="feature-card">
<div class="feature-icon">⚡</div>
<h3>Async First</h3>
<p>Built on ASGI from day one. Handles thousands of concurrent requests with full async/await support.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🤖</div>
<h3>Built-in AI</h3>
<p>Claude and OpenAI support out of the box. Chat, streaming, RAG, and agents — 3 lines of code.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🗄️</div>
<h3>Async ORM</h3>
<p>SQLAlchemy async with auto migrations, repository pattern, and one-command CRUD generation.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🔐</div>
<h3>Auth Built-in</h3>
<p>JWT tokens, refresh tokens, RBAC, API keys, and password hashing — all ready to use.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🖥️</div>
<h3>Admin Panel</h3>
<p>Auto-generated dark/light mode admin UI for any model. No extra setup needed.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🔌</div>
<h3>WebSockets</h3>
<p>Real-time connections with JSON messaging, path parameters, and AI streaming support.</p>
</div>

<div class="feature-card">
<div class="feature-icon">📄</div>
<h3>Document AI</h3>
<p>PDF extraction, image OCR via Claude Vision, document Q&A, and structured data extraction.</p>
</div>

<div class="feature-card">
<div class="feature-icon">⚙️</div>
<h3>Background Jobs</h3>
<p>Async job queue with automatic retry, exponential backoff, and interval scheduling.</p>
</div>

<div class="feature-card">
<div class="feature-icon">📊</div>
<h3>Monitoring</h3>
<p>Live dashboard, health checks, request metrics, CPU/memory usage — zero configuration.</p>
</div>

<div class="feature-card">
<div class="feature-icon">🛡️</div>
<h3>Rate Limiting</h3>
<p>Per-IP rate limiting middleware with automatic 429 responses and Retry-After headers.</p>
</div>

<div class="feature-card">
<div class="feature-icon">📧</div>
<h3>Email</h3>
<p>Send emails in 2 lines. SMTP with TLS/SSL, HTML support, CC, BCC — async and non-blocking.</p>
</div>

<div class="feature-card">
<div class="feature-icon">📖</div>
<h3>OpenAPI / Swagger</h3>
<p>Auto-generated API documentation at /docs and /redoc — no extra code needed.</p>
</div>

</div>

---

## 60 Seconds to a Full AI App

```python
from shakti import Shakti, Depends
from shakti.config import Config
from shakti.orm import Database
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

**You now have:**

- ✅ REST API with JWT auth
- ✅ AI chat at `POST /ai/chat`
- ✅ WebSocket AI streaming at `ws://localhost:8000/ws/chat`
- ✅ Admin panel at `/admin/`
- ✅ Monitoring dashboard at `/monitor/`
- ✅ Background job queue
- ✅ OpenAPI docs at `/docs`

---

## Auto CRUD Generation

Generate a complete API in one command:

```bash
# Create model + full CRUD endpoints
shakti generate api Post title:str body:text views:int

# Run migrations
shakti makemigrations "add posts"
shakti migrate
```

You instantly get:

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/posts` | List all posts |
| `POST` | `/posts` | Create a post |
| `GET` | `/posts/{id}` | Get one post |
| `PUT` | `/posts/{id}` | Update a post |
| `DELETE` | `/posts/{id}` | Delete a post |

---

## Sample Response

Hit any auto-generated endpoint and get clean JSON back, no boilerplate:

```bash
curl http://127.0.0.1:8000/posts
```

```json
[
  {
    "id": 1,
    "title": "Hello, Shakti",
    "body": "My first post using Shakti Framework.",
    "views": 42
  },
  {
    "id": 2,
    "title": "Async ORM in action",
    "body": "Migrations, repositories, and CRUD in one command.",
    "views": 17
  }
]
```

---

## Install

=== "Everything"

    ```bash
    pip install "shakti-framework[all]"
    ```

=== "Pick modules"

    ```bash
    pip install "shakti-framework[server]"      # + uvicorn
    pip install "shakti-framework[orm]"         # + SQLAlchemy
    pip install "shakti-framework[auth]"        # + JWT + bcrypt
    pip install "shakti-framework[ai]"          # + Claude/OpenAI
    pip install "shakti-framework[monitoring]"  # + psutil
    ```

=== "Core only"

    ```bash
    pip install shakti-framework
    ```

---

## Quick Start

```bash
pip install "shakti-framework[all]"
shakti new myapp
cd myapp
shakti run --reload
```

Open `http://127.0.0.1:8000` — your app is running. 🚀

<div class="cta-buttons" style="margin-top: 3rem;">
  <a href="getting-started/installation/" class="cta-primary">Read the Docs →</a>
  <a href="https://pypi.org/project/shakti-framework/" class="cta-secondary">📦 View on PyPI</a>
</div>

---

<div style="text-align: center; padding: 2rem 0; color: var(--md-default-fg-color--light); font-size: 0.9rem;">
  MIT License · Built by <a href="https://adityabhat.in">Aditya Bhat</a> · 
  <span style="background: linear-gradient(to right, #FF9933, #138808); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700;">Made in India 🇮🇳</span>
</div>
