---
description: API key authentication in Shakti Python Framework for service-to-service and webhook requests, via the X-API-Key header.
---

# API Keys

For service-to-service or webhook auth where a JWT login flow doesn't make sense, `Auth` also supports long-lived API keys sent via an `X-API-Key` header.

## Issuing a key

```python
raw_key, api_key = await auth.create_api_key(user, name="CI pipeline")
print(raw_key)  # show/store this once — it is never retrievable again
```

`create_api_key` generates a 32-byte random token (`secrets.token_hex(32)`), stores only its bcrypt hash (`api_key.key_hash`) in the `api_keys` table, and returns the raw key alongside the `APIKey` row. Treat the raw key like a password: display it to the user once, then discard it — there's no way to recover it from the stored hash.

## Protecting a route with an API key

```python
from shakti import Depends
from shakti.auth.models import User

@app.get("/webhook")
async def webhook(user: User = Depends(auth.get_api_key_user())) -> dict:
    ...
```

`get_api_key_user()` reads the `X-API-Key` header, checks it (via `bcrypt`) against every active key's hash, and resolves the owning `User` — raising `401` if the header is missing, no key matches, or the matching key's user is inactive.

```bash
curl -H "X-API-Key: <raw_key>" https://api.example.com/webhook
```

Because verification checks the raw key against every active hash, lookup cost grows with the number of active keys — fine for typical service-key volumes, but if you're issuing keys at large scale, consider adding an indexed lookup prefix to your own key format rather than relying on the linear scan.

## Revoking a key

```python
await auth.revoke_api_key(api_key.id)
```

Sets `is_active = False`; revoked keys fail `get_api_key_user()` immediately (a `401`, not a `404` — the header format doesn't reveal whether the key ever existed).

## The `APIKey` model

`shakti.auth.models.APIKey`: `id`, `user_id` (FK → `users.id`), `name`, `key_hash`, `is_active`, plus `created_at`/`updated_at`. A user can hold multiple keys (`user.api_keys` relationship) — issue one per integration so you can revoke them independently.

Combine with [RBAC](rbac.md) if API-key clients should be restricted the same way as logged-in users — `get_api_key_user()` resolves the same `User` object `require_role()` checks against, so you can chain your own dependency that does both if needed.
