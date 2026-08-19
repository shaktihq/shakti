---
title: Shakti vs FastAPI
description: How Shakti Python Framework compares to FastAPI — batteries-included vs minimal, request validation, ORM, auth, and admin tooling.
---

# Shakti vs FastAPI

FastAPI and Shakti are both async, ASGI-based Python web frameworks, but they solve different problems by design. This is a structural comparison, not a benchmark — we haven't published performance numbers for either, and you shouldn't trust a framework comparison that invents them.

## Where FastAPI is deliberately minimal

FastAPI's core strength is request/response validation and automatic OpenAPI documentation, built on Pydantic. It doesn't ship an ORM, an auth system, or an admin panel — and that's intentional. You choose SQLAlchemy or Tortoise or nothing at all; you choose your own auth library; you assemble the stack that fits your project.

That's a real advantage when you already have strong opinions about your ORM, your auth flow, or your deployment shape, and don't want a framework making those choices for you.

## Where Shakti is opinionated

Shakti bundles the pieces most APIs end up needing anyway:

```python
from shakti import Shakti, Depends
from shakti.orm import Database
from shakti.auth import Auth
from shakti.admin import Admin

app = Shakti(title="My App")
db = Database("sqlite+aiosqlite:///./app.db")
db.init_app(app)

auth = Auth(db, secret_key="...")
auth.init_app(app)

admin = Admin(db, auth)
admin.init_app(app)
```

That's a database connection, JWT authentication, and a working admin UI, with no separate library choices to make. See [Getting Started](../getting-started/installation.md).

## One honest gap: request validation

FastAPI's Pydantic-based request validation is genuinely strong, and it's worth naming directly: Shakti doesn't have an equivalent typed-schema validation layer yet. Handlers take a plain `dict` body today — see [Request & Response](../core/request-response.md). If automatic request-schema validation with field-level error messages is the feature you rely on most, that's currently a point in FastAPI's favor.

## Where Shakti goes further

- **Admin panel** — register a model, get a working CRUD UI. FastAPI has no built-in equivalent.
- **AI integration** — chat, streaming, RAG, and tool-calling agents are first-class, not a third-party add-on. See [AI Overview](../ai/overview.md).
- **Background jobs** — an async job queue with retries and scheduling is built in. See [Workflows](../workflows.md).
- **Auth + RBAC** — JWT, refresh tokens, and role-based access control ship ready to use. See [JWT Auth](../auth/jwt.md).

## Which one fits

If you want maximum control over every dependency and already have a validation/ORM/auth stack you like, FastAPI's minimalism is a feature. If you want an API, an admin UI, and AI features running from a single install without assembling them yourself, Shakti is built for that. Both are legitimate choices — they're just optimizing for different defaults.
