"""Auth models: User and APIKey."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

from shakti.orm import Base, Field, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = Field(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = Field(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = Field(String(255), nullable=False)
    is_active: Mapped[bool] = Field(Boolean, default=True, nullable=False)
    role: Mapped[str] = Field(String(50), default="user", nullable=False)
    refresh_token: Mapped[str | None] = Field(String(512), nullable=True)

    api_keys: Mapped[list[APIKey]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class APIKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    user_id: Mapped[int] = Field(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = Field(String(100), nullable=False)
    key_hash: Mapped[str] = Field(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = Field(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name!r}>"
