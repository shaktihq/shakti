---
description: Release notes and changelog for the Shakti Python Framework — new features, fixes, and security updates by version.
---

# Changelog

## 0.2.5

**Fixes**

- Admin edit/create forms were completely broken for any model using `TimestampMixin` (including `User`, and anything `shakti generate` scaffolds by default) — datetime fields had no form-value conversion and were incorrectly required. Columns with a `server_default` (like `created_at`/`updated_at`) are now automatically read-only, and datetime input is now parsed correctly. See [Admin Panel](admin.md#modeladmin-options).
- The monitoring dashboard rendered health-check messages, endpoint paths, and recent-request paths without HTML-escaping — the same class of issue fixed in the admin panel in 0.2.4. Fixed; `/monitor/` has no auth in front of it by default, so this is worth upgrading for even if you don't use the admin panel.
- Fixed a regression from 0.2.4's endpoint-metrics grouping fix: "recent requests" was showing the route template (`/posts/{id:int}`) instead of the literal path that was actually hit (`/posts/42`).

## 0.2.4

**Fixes — all security-relevant, upgrade recommended**

- `import shakti` crashed with `ModuleNotFoundError` on a bare `pip install shakti-framework` — `Admin`/`Auth` were imported eagerly, pulling in `sqlalchemy`/`bcrypt`/`PyJWT` even if you never touch those features. `Admin`, `Auth`, `APIKey`, and `User` are now loaded lazily; the base install only needs `pyyaml`.
- **Admin panel**: `Admin(db)` without `auth=` silently signed session cookies with a hardcoded, publicly-known default secret key — anyone could forge an admin session. Now raises `ValueError` at startup instead; there is no default. See [Admin Panel: Signing key](admin.md#signing-key).
- **Admin panel**: the entire UI (list/edit views, search, flash messages, activity log) rendered database and request values into HTML with no escaping — a stored/reflected XSS hole reachable by any regular app user, not just an admin. Every interpolation point is now HTML-escaped.
- **Admin panel**: CSV export didn't sanitize cell values, so a field containing `=HYPERLINK(...)` (set by any app user) would execute as a formula when an admin opened the export in Excel/Sheets. Cells are now neutralized per the standard CWE-1236 mitigation.
- `WorkflowEngine`: retry-backoff timers were untracked `asyncio` tasks, so `queue.stop()` never cancelled them, and a job waiting to retry couldn't be cancelled (only `PENDING` jobs could). Both fixed.
- `Cache`: in-memory eviction wasn't actually LRU — it evicted whichever entry had the soonest TTL, so a permanent (`ttl=0`) entry was evicted first instead of protected. Now a real `OrderedDict`-backed LRU.
- `Monitor`: per-endpoint metrics were keyed by the raw request path, so every unique id on a parameterized route (`/posts/1`, `/posts/2`, ...) created its own permanent, never-evicted dict entry — an unbounded memory leak, and an unauthenticated way to grow memory by hitting garbage 404 paths. Now grouped by the matched route's template.
- `hatchling<1.32` and `twine>=7.0` pinned in the publish pipeline for PyPI compatibility.

## 0.2.3 / 0.2.2

**Added**

- `app.static(path, directory)` — static file serving via `StaticFiles`/`FileResponse`. Missing assets always return a real `404` (never an SPA-fallback `200`); content-hashed filenames get `Cache-Control: public, immutable, max-age=31536000`. See [Routing: static files](core/routing.md#static-files).
- `SecurityHeadersMiddleware` — `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` on by default; opt-in `Content-Security-Policy`/`Permissions-Policy`. See [Middleware](core/middleware.md#securityheadersmiddleware).

**Docs**

- Filled in real content for 22 previously-stubbed pages across Core, Auth, ORM, AI, Workflows, Document AI, CLI, and Deployment.
