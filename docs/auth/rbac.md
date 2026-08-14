# RBAC

Shakti's role-based access control is deliberately simple: every `User` has a single `role` string column (default `"user"`), and `Auth.require_role()` gives you a dependency that enforces it.

## Restricting a route to specific roles

```python
from shakti import Depends
from shakti.auth.models import User

@app.delete("/admin/users/{id:int}")
async def delete_user(id: int, user: User = Depends(auth.require_role("admin"))) -> dict:
    ...
```

`require_role(*roles)` first verifies the JWT (same as `get_current_user()` — `401` for missing/invalid/expired tokens), then checks `user.role` against the allowed set, raising `403` with a message naming both the required and actual role if it doesn't match:

```python
@app.get("/reports")
async def reports(user: User = Depends(auth.require_role("admin", "analyst"))) -> dict:
    # allowed if user.role is "admin" OR "analyst"
    ...
```

## Assigning roles

Roles are set at registration or afterward:

```python
admin = await auth.register_user(
    email="admin@example.com", username="admin", password="...", role="admin",
)
```

```python
# POST /auth/register
{"email": "a@b.com", "username": "alice", "password": "s3cret", "role": "admin"}
```

To change a user's role later, update it through your own ORM code — there's no built-in "promote user" endpoint, since who's allowed to grant roles is application-specific:

```python
async with db.session() as session:
    user = await session.get(User, user_id)
    user.role = "admin"
    await session.commit()
```

## Roles are just strings

There's no fixed enum of roles — `role` is a free-form `String(50)` column, so you can use whatever scheme fits (`"user"`/`"admin"`, or `"viewer"`/`"editor"`/`"owner"`, etc.). If you need more granular permissions than one role per user (e.g. per-resource ACLs), layer that on top with your own `Depends()` dependency that reads from your own tables — `require_role` covers the common "is this user in role X" case, not general authorization.

See [JWT Auth](jwt.md) for how tokens and `Depends(auth.get_current_user())` work under the hood.
