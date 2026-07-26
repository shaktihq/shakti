"""Declarative base and reusable mixins."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """All models inherit from this class.

    Provides a ``__tablename__`` derived automatically from the class name
    (snake_case plural) and an integer primary key ``id``.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    @classmethod
    def __tablename_from_class__(cls) -> str:
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return f"{name}s"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "__tablename__" not in cls.__dict__:
            import re
            name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
            cls.__tablename__ = f"{name}s"

    def to_dict(self) -> dict:
        """Return all mapped columns as a plain dict."""
        return {
            col.key: getattr(self, col.key)
            for col in self.__mapper__.column_attrs
        }

    def __repr__(self) -> str:
        pk = getattr(self, "id", None)
        return f"<{type(self).__name__} id={pk}>"


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
