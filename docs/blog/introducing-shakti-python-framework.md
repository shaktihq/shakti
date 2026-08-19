---
title: Introducing Shakti Python Framework
description: Why Shakti Python Framework exists — an AI-first, async Python web framework that bundles routing, ORM, auth, admin, and AI into one install.
---

# Introducing Shakti Python Framework

Most Python web projects today start the same way: pick a routing framework, then spend the next few days wiring up an ORM, an auth system, an admin panel, and — increasingly — an AI provider. Each piece comes from a different library, with its own conventions, its own version-compatibility surface, and its own documentation to learn.

**Shakti Python Framework** exists to close that gap. It's an open-source, AI-first Python web framework built on async ASGI from day one, with the pieces most APIs eventually need shipped in a single install instead of assembled by hand.

## What "AI-first" actually means here

A lot of frameworks bolt AI support on as an afterthought — a community package that wraps an HTTP client around a chat API. Shakti treats AI as a first-class subsystem, the same way it treats routing or the ORM:

```python
from shakti import AI

ai = AI(config)
ai.init_app(app)
```

That gives you a working `POST /ai/chat` endpoint, plus a Python API for chat, streaming, retrieval-augmented generation (RAG), and tool-calling agents — backed by Anthropic or OpenAI, switchable via config. See [AI Overview](../ai/overview.md).

## What's in the box

- **Routing** — typed path converters, middleware groups, WebSocket routes, static file serving with production-sane cache headers.
- **Async ORM** — SQLAlchemy 2.x under the hood, a repository pattern for common CRUD, and one-command migration generation via Alembic.
- **Auth** — JWT access/refresh tokens, role-based access control, and API keys, all backed by the same `User` model.
- **Admin panel** — register a model, get a working dark/light-mode CRUD UI with search, CSV export, and an activity log. No template to write.
- **Background jobs** — an async job queue with retries, exponential backoff, and interval scheduling.
- **Monitoring** — a live dashboard, health checks, and request metrics with zero configuration.

Every piece is designed to compose with the others — the admin panel reads the same `User` model your auth system issues tokens for; the AI module's routes go through the same request/response pipeline as everything else.

## Who it's for

If you're building an API, a full web app, or an AI agent in Python and want a shorter path from `pip install` to a running, database-backed, authenticated service, Shakti is built for that. If you want to see how it stacks up against what you're already using, read [Shakti vs FastAPI](shakti-vs-fastapi.md) or [Shakti vs Django](shakti-vs-django.md).

## Try it

```bash
pip install "shakti-framework[all]"
shakti new myapp
cd myapp
shakti run --reload
```

Start with [Your First App](../getting-started/first-app.md) for a full walkthrough, or the [Quick Start](../getting-started/quickstart.md) for the condensed version.
