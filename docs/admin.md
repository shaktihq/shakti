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
