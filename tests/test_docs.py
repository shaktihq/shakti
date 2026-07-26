"""Phase 5: Document AI tests."""

from __future__ import annotations

import asyncio
import base64
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shakti.ai.ai import AI
from shakti.ai.providers.base import AIResponse, Message
from shakti.docs import DocumentAI
from shakti.docs.extractors import extract_text
from shakti.docs.storage import Document, DocumentStore
from shakti import Shakti
from shakti.testing import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_ai() -> AI:
    with patch("shakti.ai.ai._make_provider") as mock_make:
        mock_provider = MagicMock()
        mock_provider.name = "anthropic"
        mock_provider.complete = AsyncMock(return_value=AIResponse(
            content='{"type": "report", "confidence": 0.9, "language": "English", "summary": "A test document"}',
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=10,
            output_tokens=5,
        ))

        async def mock_stream(*a, **kw):
            yield "hello"

        mock_provider.stream = mock_stream
        mock_make.return_value = mock_provider
        return AI(api_key="test-key", provider="anthropic")


def _make_docs(ai=None) -> DocumentAI:
    return DocumentAI(ai or _make_mock_ai())


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _pdf_bytes() -> bytes:
    """Minimal valid PDF with one page of text."""
    try:
        import pypdf
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception:
        return b"%PDF-1.4 minimal"


# ---------------------------------------------------------------------------
# Storage tests
# ---------------------------------------------------------------------------

def test_document_store_add_get():
    store = DocumentStore()
    doc = Document(id="1", filename="test.txt", content_type="text/plain", text="hello")
    store.add(doc)
    assert store.get("1") is doc
    assert len(store) == 1


def test_document_store_delete():
    store = DocumentStore()
    doc = Document(id="2", filename="x.txt", content_type="text/plain", text="x")
    store.add(doc)
    assert store.delete("2") is True
    assert store.get("2") is None
    assert store.delete("2") is False


def test_document_to_dict():
    doc = Document(id="3", filename="a.pdf", content_type="application/pdf", text="abc", char_count=3)
    d = doc.to_dict()
    assert d["id"] == "3"
    assert d["filename"] == "a.pdf"
    assert d["char_count"] == 3


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

def test_extract_text():
    result = asyncio.run(extract_text(b"Hello Shakti!"))
    assert result == "Hello Shakti!"


def test_extract_text_utf8():
    result = asyncio.run(extract_text("Héllo wörld".encode("utf-8")))
    assert "Héllo" in result


# ---------------------------------------------------------------------------
# DocumentAI process tests
# ---------------------------------------------------------------------------

def test_process_text_document():
    docs = _make_docs()
    text = "Shakti is an AI-first Python web framework. It supports async routing and JWT auth."
    content = text.encode()
    doc = asyncio.run(docs.process(content, "notes.txt", "text/plain"))
    assert doc.id
    assert doc.filename == "notes.txt"
    assert doc.char_count > 0
    assert len(doc.chunk_ids) > 0
    assert len(docs._store) == 1
    assert len(docs._rag) > 0


def test_process_empty_raises():
    docs = _make_docs()
    with pytest.raises(ValueError, match="Could not extract"):
        asyncio.run(docs.process(b"   ", "empty.txt", "text/plain"))


def test_process_multiple_docs():
    docs = _make_docs()
    asyncio.run(docs.process(b"First document content.", "doc1.txt", "text/plain"))
    asyncio.run(docs.process(b"Second document content.", "doc2.txt", "text/plain"))
    assert len(docs._store) == 2


# ---------------------------------------------------------------------------
# Ask tests
# ---------------------------------------------------------------------------

def test_ask_no_docs():
    docs = _make_docs()
    result = asyncio.run(docs.ask("What is this?"))
    assert "No documents" in result["answer"]


def test_ask_with_docs():
    ai = _make_mock_ai()
    ai._provider.complete = AsyncMock(return_value=AIResponse(
        content="Shakti is an AI-first framework.",
        model="claude-sonnet-4-6", provider="anthropic"
    ))
    docs = DocumentAI(ai)
    asyncio.run(docs.process(b"Shakti is an AI-first Python framework.", "info.txt", "text/plain"))
    result = asyncio.run(docs.ask("What is Shakti?"))
    assert "answer" in result
    assert "sources" in result


# ---------------------------------------------------------------------------
# Summarize tests
# ---------------------------------------------------------------------------

def test_summarize():
    ai = _make_mock_ai()
    ai._provider.complete = AsyncMock(return_value=AIResponse(
        content="This document describes Shakti framework.",
        model="claude-sonnet-4-6", provider="anthropic"
    ))
    docs = DocumentAI(ai)
    doc = asyncio.run(docs.process(b"Shakti is great for building APIs.", "readme.txt", "text/plain"))
    result = asyncio.run(docs.summarize(doc.id))
    assert result["doc_id"] == doc.id
    assert "summary" in result


def test_summarize_missing_doc():
    docs = _make_docs()
    from shakti.exceptions import HTTPException
    with pytest.raises(HTTPException) as exc:
        asyncio.run(docs.summarize("nonexistent"))
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Extract structured tests
# ---------------------------------------------------------------------------

def test_extract_structured():
    ai = _make_mock_ai()
    ai._provider.complete = AsyncMock(return_value=AIResponse(
        content='{"company": "Shakti Inc", "amount": 1000}',
        model="claude-sonnet-4-6", provider="anthropic"
    ))
    docs = DocumentAI(ai)
    doc = asyncio.run(docs.process(b"Invoice from Shakti Inc for $1000.", "invoice.txt", "text/plain"))
    result = asyncio.run(docs.extract_structured(doc.id, {"company": "string", "amount": "number"}))
    assert result["extracted"]["company"] == "Shakti Inc"
    assert result["extracted"]["amount"] == 1000


# ---------------------------------------------------------------------------
# HTTP route tests
# ---------------------------------------------------------------------------

def test_docs_routes():
    ai = _make_mock_ai()
    docs = DocumentAI(ai)
    app = Shakti()
    ai.init_app(app)
    docs.init_app(app)
    client = TestClient(app)

    r = client.get("/docs/info")
    assert r.status_code == 200
    assert r.json()["documents"] == 0


def test_upload_and_list():
    ai = _make_mock_ai()
    docs = DocumentAI(ai)
    app = Shakti()
    ai.init_app(app)
    docs.init_app(app)
    client = TestClient(app)

    r = client.post("/docs/upload", json={
        "filename": "hello.txt",
        "content": _b64("Hello from Shakti!"),
        "content_type": "text/plain",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["document"]["filename"] == "hello.txt"
    doc_id = data["document"]["id"]

    r2 = client.get("/docs/list")
    assert r2.status_code == 200
    assert len(r2.json()) == 1

    r3 = client.get(f"/docs/{doc_id}")
    assert r3.status_code == 200
    assert "text_preview" in r3.json()


def test_upload_missing_fields():
    ai = _make_mock_ai()
    docs = DocumentAI(ai)
    app = Shakti()
    ai.init_app(app)
    docs.init_app(app)
    client = TestClient(app)

    r = client.post("/docs/upload", json={"filename": "x.txt"})
    assert r.status_code == 422

    r = client.post("/docs/upload", json={"content": _b64("hi")})
    assert r.status_code == 422


def test_delete_doc():
    ai = _make_mock_ai()
    docs = DocumentAI(ai)
    app = Shakti()
    ai.init_app(app)
    docs.init_app(app)
    client = TestClient(app)

    r = client.post("/docs/upload", json={
        "filename": "del.txt",
        "content": _b64("delete me"),
        "content_type": "text/plain",
    })
    doc_id = r.json()["document"]["id"]

    r2 = client.delete(f"/docs/{doc_id}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] == doc_id

    r3 = client.get(f"/docs/{doc_id}")
    assert r3.status_code == 404
