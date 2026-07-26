"""In-memory document store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Document:
    id: str
    filename: str
    content_type: str
    text: str
    chunk_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    page_count: int = 0
    char_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "content_type": self.content_type,
            "char_count": self.char_count,
            "page_count": self.page_count,
            "chunk_count": len(self.chunk_ids),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class DocumentStore:
    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    def add(self, doc: Document) -> None:
        self._docs[doc.id] = doc

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def all(self) -> list[Document]:
        return list(self._docs.values())

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._docs:
            del self._docs[doc_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._docs)
