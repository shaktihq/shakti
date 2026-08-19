---
description: JWT authentication in Shakti Python Framework — built-in register, login, refresh, and logout routes with bcrypt password hashing.
---

# JWT Auth

`Auth` wires up JWT-based authentication — registration, login, refresh, logout — backed by your ORM's `User` model, with almost no boilerplate.

## Setup

```python
from shakti import Auth, Config
from shakti.orm.database import Database

config = Config()
db = Database(config.require("db.url"))
auth = Auth(db, secret_key=config.require("auth.secret_key"))
auth.init_app(app)
```

`init_app` does two things: registers `Auth` in the DI container (so `Depends(...)` and container injection can find it), and mounts an auth router at `prefix` (default `/auth`).

Constructor options:

| Parameter | Default | Meaning |
|---|---|---|
| `secret_key` | — required | HMAC signing key for JWTs |
| `algorithm` | `"HS256"` | `PyJWT` algorithm |
| `access_token_expire_minutes` | `30` | access token lifetime |
| `refresh_token_expire_days` | `7` | refresh token lifetime |
| `prefix` | `"/auth"` | mount point for the built-in routes |

## Built-in routes

Mounted automatically under `prefix`:

| Route | Body | Returns |
|---|---|---|
| `POST /auth/register` | `{email, username, password, role?}` | `{message, user}` |
| `POST /auth/login` | `{email, password}` | `{access_token, refresh_token, token_type, user}` |
| `POST /auth/refresh` | `{refresh_token}` | `{access_token, refresh_token, token_type}` |
| `POST /auth/logout` | — (Bearer token) | `{message}` |
| `GET /auth/me` | — (Bearer token) | the current user |

`login` and `refresh` persist the issued refresh token on the `User` row, so `refresh` and `logout` can invalidate it server-side (revoking a refresh token means it no longer matches what's stored). Passwords are hashed with `bcrypt`; they're never stored or returned in plaintext.

## Protecting routes

`auth.get_current_user()` returns a dependency that verifies the `Authorization: Bearer <token>` header and resolves the `User`:

```python
from shakti import Depends
from shakti.auth.models import User

@app.get("/me")
async def me(user: User = Depends(auth.get_current_user())) -> dict:
    return user.to_dict()
```

It raises `401` if the header is missing/malformed, the token is expired or invalid, the token isn't an access token (refresh tokens are rejected here), or the user no longer exists / is inactive.

## The `User` model

`shakti.auth.models.User` (SQLAlchemy model, via Shakti's ORM — see [ORM: Models](../orm/models.md)) has `id`, `email`, `username`, `hashed_password`, `is_active`, `role`, `refresh_token`, plus `created_at`/`updated_at` from `TimestampMixin`. `user.to_dict()` returns the public-safe fields (never `hashed_password` or `refresh_token`).

## Managing users programmatically

```python
user = await auth.register_user(email="a@b.com", username="alice", password="s3cret", role="admin")
```

Raises `409` if the email or username is already taken.

## Custom claims

Access tokens are issued with `sub` (user id) and `role` claims; refresh tokens carry just `sub`. If you need more in the token, use `shakti.auth.tokens.create_access_token(payload, secret, ...)` directly rather than `Auth`'s built-in login flow.

See [RBAC](rbac.md) for role-based restrictions and [API Keys](api-keys.md) for non-JWT service-to-service auth.
