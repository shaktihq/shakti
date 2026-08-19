---
title: Shakti Admin Panel Walkthrough
description: A walkthrough of the Shakti admin panel — register a model, get a dark/light-mode CRUD UI with search, CSV export, and an activity log.
---

# Shakti Admin Panel Walkthrough

Every ORM-backed app eventually needs an internal screen for support staff or admins to look up and fix records. The [Shakti admin panel](../admin.md) exists so you don't have to build that screen by hand.

## Register a model

```python
from shakti.admin import Admin
from app.models.post import Post

admin = Admin(db, auth, title="My Admin")
admin.register(Post,
    list_fields=["id", "title", "created_at"],
    search_fields=["title", "body"],
)
admin.init_app(app)
```

Visit `/admin/`, log in with any user whose `role` is `"admin"`, and you have a working list view, search, create/edit forms, and delete — generated entirely from your model's columns.

## What you get without writing any UI code

- **List views** with pagination and search across the fields you specify
- **Create/edit forms**, auto-generated from column types — a `Boolean` column becomes a checkbox, a `DateTime` becomes a datetime picker, a `Text` column becomes a textarea
- **CSV export** on every registered model
- **An activity log** — who created, updated, or deleted what, and when
- **Dark and light mode**, toggleable, no extra setup

## Read-only fields happen automatically too

Any column with a database-managed default — like the `created_at`/`updated_at` timestamps every model gets from `TimestampMixin` — is automatically treated as read-only in the admin form. You don't have to remember to exclude them yourself; see [ModelAdmin options](../admin.md#modeladmin-options).

## It's not a separate app

The admin panel runs inside your existing Shakti app, sharing the same database session handling, the same `User`/`Auth` system for login, and the same request pipeline as your API routes. There's no separate admin service to deploy or keep in sync.

## Security, by default

Field values, search queries, and activity-log entries are HTML-escaped before rendering, and CSV exports sanitize cells that could be interpreted as spreadsheet formulas — the admin panel is safe to point at real user-submitted data out of the box. See [Admin Panel: Security](../admin.md#security) for details.

## Try it

If you already have a model, registering it takes three lines. If you're starting from scratch, [Build a REST API with Shakti](build-rest-api-with-shakti.md) walks through creating one first.
