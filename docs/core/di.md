# Dependency Injection

Shakti binds handler parameters automatically by inspecting each handler's signature — no decorators needed on the parameters themselves. For every parameter, in order:

1. Default is `Depends(...)` → resolved as a dependency (see below).
2. Annotated `Request` (or named `request` with no annotation) → the current request.
3. Name matches a path parameter → converted to the annotated type.
4. Annotation is registered in the container → resolved from the container.
5. Name is `body` → the parsed JSON request body.
6. Name matches a query parameter → converted to the annotated type.
7. Parameter has a default value → used as-is.
8. Otherwise → `422 Unprocessable Entity`.

```python
@app.get("/posts/{post_id:int}")
async def get_post(post_id: int, request: Request, db: Database) -> dict:
    ...  # post_id: path param, request: current request, db: container-resolved
```

## The container

Every `Shakti` app has a `Container` (`app.container`) used for step 4 above. Register instances or factories:

```python
app.container.register_instance(Database, db)          # a fixed instance
app.container.register(Cache, lambda: Cache(config))     # a factory, memoized (singleton=True by default)
app.container.register(Logger, make_logger, singleton=False)  # a new instance per resolve()
```

Any type registered this way can then just show up as a type-annotated handler parameter and Shakti will supply it — no explicit `Depends()` required. `Config` and the `Shakti` app instance itself are registered automatically.

## `Depends()`

For request-scoped dependencies that need their own logic (auth checks, per-request setup) rather than a container lookup, use `Depends`:

```python
from shakti import Depends

async def current_user(request: Request, auth: Auth) -> User:
    token = request.headers.get("authorization", "").removeprefix("Bearer ")
    return await auth.get_user(token)

@app.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email}
```

`Depends(dependency)` resolves `dependency` the same way a handler is resolved (recursively, with the same binding rules) — so a dependency can itself take `request`, other `Depends(...)`, or container-registered services.

By default, results are cached per-request: if two parameters (or a dependency and a handler) both depend on `current_user`, it only runs once. Pass `use_cache=False` to force it to re-run:

```python
user: User = Depends(current_user, use_cache=False)
```

## Type conversion

Path and query parameters arrive as strings and get converted to the annotated type (`int`, `float`, `bool`, or any callable single-arg constructor). Booleans accept `1/true/yes/on` and `0/false/no/off` (case-insensitive). A conversion failure raises `422` with a message naming the offending parameter.
