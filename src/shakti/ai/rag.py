"""Simple RAG (Retrieval-Augmented Generation) — no external vector DB needed.

Uses TF-IDF cosine similarity for retrieval. Good for up to ~10k documents.
For production, swap out _score() with embeddings from your AI provider.

Usage::

    from shakti.ai.rag import RAGStore

    rag = RAGStore()
    rag.add("Shakti is a Python web framework.", metadata={"source": "docs"})
    rag.add("Django is a Python web framework.", metadata={"source": "docs"})

    results = rag.search("what is shakti?", k=3)
    context = rag.build_context(results)
"""

from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z0-9]+\b", text.lower())


def _tf(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


def _idf(term: str, corpus: list[list[str]]) -> float:
    n = len(corpus)
    df = sum(1 for doc in corpus if term in doc) + 1
    return math.log((n + 1) / df) + 1


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (mag_a * mag_b + 1e-10)


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


class RAGStore:
    """In-memory TF-IDF document store for retrieval-augmented generation."""

    def __init__(self, chunk_size: int = 300, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._chunks: list[Chunk] = []
        self._token_cache: list[list[str]] = []

    def add(
        self,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
    ) -> list[str]:
        """Add a document, split into chunks. Returns list of chunk IDs."""
        chunks = _chunk_text(text, self.chunk_size, self.overlap)
        ids = []
        base_meta = {**(metadata or {}), "source_id": source_id or str(uuid.uuid4())}
        for i, chunk_text in enumerate(chunks):
            cid = str(uuid.uuid4())
            self._chunks.append(Chunk(id=cid, text=chunk_text, metadata={**base_meta, "chunk_index": i}))
            self._token_cache.append(_tokenize(chunk_text))
            ids.append(cid)
        return ids

    def search(self, query: str, k: int = 5) -> list[Chunk]:
        """Find the top-k most relevant chunks for a query."""
        if not self._chunks:
            return []
        q_tokens = _tokenize(query)
        q_tf = _tf(q_tokens)
        scored = []
        for chunk, tokens in zip(self._chunks, self._token_cache):
            c_tf = _tf(tokens)
            # Weight by IDF
            weighted_q = {t: v * _idf(t, self._token_cache) for t, v in q_tf.items()}
            weighted_c = {t: v * _idf(t, self._token_cache) for t, v in c_tf.items()}
            score = _cosine(weighted_q, weighted_c)
            scored.append(Chunk(id=chunk.id, text=chunk.text, metadata=chunk.metadata, score=score))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]

    def build_context(self, chunks: list[Chunk], max_chars: int = 2000) -> str:
        """Format retrieved chunks into a context string for the prompt."""
        parts = []
        total = 0
        for i, chunk in enumerate(chunks, 1):
            src = chunk.metadata.get("source", chunk.metadata.get("source_id", f"chunk-{i}"))
            part = f"[Source: {src}]\n{chunk.text}"
            if total + len(part) > max_chars:
                break
            parts.append(part)
            total += len(part)
        return "\n\n---\n\n".join(parts)

    def clear(self) -> None:
        self._chunks.clear()
        self._token_cache.clear()

    def __len__(self) -> int:
        return len(self._chunks)

    def __repr__(self) -> str:
        return f"RAGStore(chunks={len(self)})"
