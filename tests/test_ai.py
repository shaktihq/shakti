"""Phase 4: AI module tests (offline — no real API calls)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shakti.ai.ai import AI, SSEResponse
from shakti.ai.agents import Agent, _build_tool_schema
from shakti.ai.providers.base import AIResponse, Message
from shakti.ai.rag import RAGStore, _tokenize, _chunk_text
from shakti.ai.templates import PromptTemplate, SUMMARIZE, TRANSLATE
from shakti import Shakti
from shakti.testing import TestClient


# ---------------------------------------------------------------------------
# RAG tests (no API needed)
# ---------------------------------------------------------------------------

def test_rag_add_and_len():
    rag = RAGStore()
    rag.add("Shakti is a Python web framework.")
    rag.add("Django is another Python web framework.")
    assert len(rag) >= 2


def test_rag_search_returns_relevant():
    rag = RAGStore()
    rag.add("Shakti has async routing.", metadata={"source": "shakti-docs"})
    rag.add("Django uses synchronous views by default.", metadata={"source": "django-docs"})
    rag.add("SQLAlchemy is an ORM library.", metadata={"source": "sqlalchemy-docs"})

    results = rag.search("async routing shakti", k=2)
    assert len(results) > 0
    assert results[0].score > 0
    assert any("Shakti" in r.text for r in results[:2])


def test_rag_search_empty_store():
    rag = RAGStore()
    assert rag.search("anything") == []


def test_rag_build_context():
    rag = RAGStore()
    rag.add("Shakti is fast.", metadata={"source": "docs"})
    chunks = rag.search("shakti", k=1)
    ctx = rag.build_context(chunks)
    assert "Shakti" in ctx
    assert "Source:" in ctx


def test_rag_clear():
    rag = RAGStore()
    rag.add("some text")
    rag.clear()
    assert len(rag) == 0


def test_chunk_text():
    text = " ".join(["word"] * 500)
    chunks = _chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 100 for c in chunks)


def test_tokenize():
    tokens = _tokenize("Hello World! This is Shakti 2026.")
    assert "hello" in tokens
    assert "shakti" in tokens
    assert "2026" in tokens


# ---------------------------------------------------------------------------
# Prompt template tests
# ---------------------------------------------------------------------------

def test_template_render():
    tpl = PromptTemplate("Hello {name}, you are {age} years old.")
    result = tpl.render(name="Legend", age=25)
    assert result == "Hello Legend, you are 25 years old."


def test_template_variables():
    tpl = PromptTemplate("Translate {text} to {language}.")
    assert set(tpl.variables()) == {"text", "language"}


def test_template_defaults():
    tpl = PromptTemplate("Say {greeting} to {name}.", defaults={"greeting": "hello"})
    assert tpl.render(name="world") == "Say hello to world."


def test_template_missing_var_raises():
    tpl = PromptTemplate("Hello {name}")
    with pytest.raises(ValueError, match="missing variable"):
        tpl.render()


def test_builtin_summarize():
    prompt = SUMMARIZE.render(text="Shakti is great.")
    assert "Shakti is great." in prompt


def test_builtin_translate():
    prompt = TRANSLATE.render(text="Hello", language="French")
    assert "French" in prompt and "Hello" in prompt


# ---------------------------------------------------------------------------
# Tool schema generation tests
# ---------------------------------------------------------------------------

def test_build_tool_schema():
    def search_web(query: str, max_results: int = 5) -> str:
        """Search the web."""
        return ""

    schema = _build_tool_schema(search_web, "Search the web for information")
    assert schema["name"] == "search_web"
    assert "query" in schema["input_schema"]["properties"]
    assert "query" in schema["input_schema"]["required"]
    assert "max_results" not in schema["input_schema"]["required"]


# ---------------------------------------------------------------------------
# AI class tests with mocked provider
# ---------------------------------------------------------------------------

def _make_mock_ai() -> AI:
    """Create AI instance with a mocked provider (no real API calls)."""
    with patch("shakti.ai.ai._make_provider") as mock_make:
        mock_provider = MagicMock()
        mock_provider.name = "anthropic"
        mock_provider.complete = AsyncMock(return_value=AIResponse(
            content="Mocked response",
            model="claude-sonnet-4-6",
            provider="anthropic",
            input_tokens=10,
            output_tokens=5,
        ))

        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello", " world", "!"]:
                yield chunk

        mock_provider.stream = mock_stream
        mock_make.return_value = mock_provider
        ai = AI(api_key="test-key", provider="anthropic")
    return ai


def test_ai_init():
    ai = _make_mock_ai()
    assert ai.provider_name == "anthropic"
    assert ai.model == "claude-sonnet-4-6"
    assert isinstance(ai.rag, RAGStore)


def test_ai_chat():
    ai = _make_mock_ai()
    result = asyncio.run(ai.chat("Hello!"))
    assert result == "Mocked response"


def test_ai_complete_returns_response():
    ai = _make_mock_ai()
    resp = asyncio.run(ai.complete("Hello!"))
    assert isinstance(resp, AIResponse)
    assert resp.total_tokens == 15


def test_ai_stream():
    ai = _make_mock_ai()

    async def collect():
        chunks = []
        async for chunk in ai.stream("Hi"):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect())
    assert chunks == ["Hello", " world", "!"]


def test_ai_rag_chat():
    ai = _make_mock_ai()
    ai.rag.add("Shakti is an async Python framework.")
    result = asyncio.run(ai.rag_chat("what is shakti?"))
    assert "answer" in result
    assert "sources" in result


def test_ai_template():
    ai = _make_mock_ai()
    ai.register_template("greet", PromptTemplate("Say hello to {name}"))
    result = asyncio.run(ai.ask("greet", name="Legend"))
    assert result == "Mocked response"


def test_ai_unknown_template_raises():
    ai = _make_mock_ai()
    with pytest.raises(ValueError, match="Unknown template"):
        asyncio.run(ai.ask("nonexistent"))


# ---------------------------------------------------------------------------
# HTTP routes tests
# ---------------------------------------------------------------------------

def test_ai_routes():
    ai = _make_mock_ai()
    app = Shakti()
    ai.init_app(app)
    client = TestClient(app)

    # /ai/info
    r = client.get("/ai/info")
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-6"


def test_ai_chat_route():
    ai = _make_mock_ai()
    app = Shakti()
    ai.init_app(app)
    client = TestClient(app)

    r = client.post("/ai/chat", json={"message": "Hello"})
    assert r.status_code == 200
    assert r.json()["reply"] == "Mocked response"


def test_ai_chat_missing_message():
    ai = _make_mock_ai()
    app = Shakti()
    ai.init_app(app)
    client = TestClient(app)
    r = client.post("/ai/chat", json={})
    assert r.status_code == 422


def test_ai_rag_routes():
    ai = _make_mock_ai()
    app = Shakti()
    ai.init_app(app)
    client = TestClient(app)

    r = client.post("/ai/rag/add", json={"text": "Shakti is great.", "metadata": {"source": "test"}})
    assert r.status_code == 200
    assert r.json()["added_chunks"] >= 1

    r = client.post("/ai/rag/query", json={"question": "what is shakti?"})
    assert r.status_code == 200
    assert "answer" in r.json()


def test_ai_complete_route():
    ai = _make_mock_ai()
    app = Shakti()
    ai.init_app(app)
    client = TestClient(app)
    r = client.post("/ai/complete", json={"message": "Hello"})
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    assert "tokens" in data
