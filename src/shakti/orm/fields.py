"""Convenience re-exports so model files read cleanly.

Usage::

    from shakti.orm.fields import Column, Field, Integer, String, Boolean, Text, Float

``Field`` is an alias for ``mapped_column`` — the modern SQLAlchemy 2.x approach
when combined with ``Mapped[T]`` annotations.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column as Field
from sqlalchemy.orm import relationship

__all__ = [
    "Boolean",
    "Column",
    "DateTime",
    "Field",
    "Float",
    "ForeignKey",
    "Integer",
    "String",
    "Text",
    "UniqueConstraint",
    "relationship",
]
