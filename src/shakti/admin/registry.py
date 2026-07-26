"""ModelAdmin registry — configure how each model appears in the admin."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy import inspect as sa_inspect


@dataclass
class ModelAdmin:
    model: type
    list_fields: list[str] = field(default_factory=list)
    search_fields: list[str] = field(default_factory=list)
    readonly_fields: list[str] = field(default_factory=list)
    list_per_page: int = 25

    def __post_init__(self) -> None:
        if not self.list_fields:
            self.list_fields = self._auto_list_fields()
        if "id" not in self.readonly_fields:
            self.readonly_fields = ["id", *self.readonly_fields]

    def _auto_list_fields(self) -> list[str]:
        cols = [c.key for c in sa_inspect(self.model).columns]
        # Put id first, skip hashed_password / refresh_token
        hidden = {"hashed_password", "refresh_token"}
        ordered = [c for c in cols if c not in hidden]
        return ordered[:6]  # max 6 columns in list view

    @property
    def name(self) -> str:
        return self.model.__name__

    @property
    def slug(self) -> str:
        import re
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.name).lower() + "s"

    def get_fields(self) -> list[dict[str, Any]]:
        """Return field metadata for form rendering."""
        mapper = sa_inspect(self.model)
        result = []
        hidden = {"hashed_password", "refresh_token"}
        for col in mapper.columns:
            if col.key in hidden:
                continue
            sa_type = type(col.type)
            if sa_type == Text:
                input_type = "textarea"
            elif sa_type == Integer:
                input_type = "number"
            elif sa_type == Float:
                input_type = "decimal"
            elif sa_type == Boolean:
                input_type = "checkbox"
            elif sa_type == DateTime:
                input_type = "datetime"
            else:
                input_type = "text"
            result.append({
                "name": col.key,
                "type": input_type,
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "readonly": col.key in self.readonly_fields,
            })
        return result
