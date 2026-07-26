"""Chat message model."""
from sqlalchemy.orm import Mapped
from shakti.orm import Base, Field, TimestampMixin
from sqlalchemy import String, Text

class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    role: Mapped[str] = Field(String(20))
    content: Mapped[str] = Field(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
