---
description: The Shakti admin panel — an auto-generated, dark/light mode admin UI for any model, with search, CSV export, and an activity log. No extra setup.
---

# Admin Panel

Shakti includes a built-in admin panel — better than Django's.

## Setup

```python
from shakti.admin import Admin
from app.models.post import Post
from shakti.auth.models import User

admin = Admin(db, auth, title="My Admin")
admin.register(Post,
    list_fields=["id", "title", "created_at"],
    search_fields=["title", "body"]
)
admin.register(User,
    list_fields=["id", "email", "username", "role"],
    search_fields=["email", "username"]
)
admin.init_app(app)
```

Visit `http://localhost:8000/admin/`

Login with any user that has `role: "admin"`.

## Signing key

`Admin(db, auth, ...)` reuses `auth.secret_key` to sign the admin session cookie — the usual setup, no extra config. If you're not passing `auth=`, you must pass `secret_key=` explicitly:

```python
admin = Admin(db, secret_key=config.require("admin.secret_key"))
```

There is no default secret key — omitting both `auth` and `secret_key` raises `ValueError` at startup rather than silently signing sessions with a fallback, since a shared default would let anyone forge an admin session cookie.

## Features

- Dark mode and light mode toggle
- Search across any field
- Paginated list views
- Create, edit, delete records
- CSV export on any model
- Activity log (who did what)
- Hover-reveal action buttons
- Auto-dismiss flash messages

## ModelAdmin options

| Option | Default | Description |
|--------|---------|-------------|
| `list_fields` | auto (first 6) | Columns shown in list |
| `search_fields` | `[]` | Fields to search on |
| `readonly_fields` | `["id"]` | Non-editable fields |
| `list_per_page` | `25` | Records per page |

Any column with a `server_default` — e.g. `TimestampMixin`'s `created_at`/`updated_at` — is automatically treated as read-only too, on top of whatever you list in `readonly_fields`. Those columns are database-managed; there's nothing meaningful for the form to submit for them.

## Security

- All field values, search queries, and activity-log entries are HTML-escaped before rendering — data from regular app users (not just admins) can safely be displayed in list/edit views and the dashboard without risking script injection.
- CSV export sanitizes cells that start with `=`, `+`, `-`, or `@` so an exported file can't execute a formula when opened in Excel/Sheets/LibreOffice.
