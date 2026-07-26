"""Main AI class — provider abstraction, chat, streaming, RAG, agents.

Usage::

    from shakti.ai import AI

    ai = AI(config)
    ai.init_app(app)

    # Simple chat
    @app.post("/chat")
    async def chat(body: dict) -> dict:
        reply = await ai.chat(body["message"])
        return {"reply": reply}

    # With history
    @app.post("/converse")
    async def converse(body: dict) -> dict:
        history = [Message(**m) for m in body.get("history", [])]
        reply = await ai.chat(body["message"], history=history)
        return {"reply": reply}

    # RAG
    ai.rag.add("Shakti docs...", metadata={"source": "docs"})

    @app.post("/ask-docs")
    async def ask_docs(body: dict) -> dict:
        return await ai.rag_chat(body["question"])
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from shakti.ai.agents import Agent
from shakti.ai.providers.base import AIResponse, BaseProvider, Message
from shakti.ai.rag import RAGStore
from shakti.ai.templates import PromptTemplate
from shakti.exceptions import HTTPException
from shakti.http.response import Response
from shakti.routing.router import Router

if TYPE_CHECKING:
    from shakti.application import Shakti
    from shakti.config.settings import Config

logger = logging.getLogger("shakti.ai")


class SSEResponse(Response):
    """Server-Sent Events response for streaming AI output."""

    def __init__(self, generator: AsyncIterator[str]) -> None:
        self._generator = generator
        super().__init__(b"", status_code=200, media_type="text/event-stream")

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/event-stream; charset=utf-8"),
                (b"cache-control", b"no-cache"),
                (b"x-accel-buffering", b"no"),
                (b"access-control-allow-origin", b"*"),
            ],
        })
        try:
            async for chunk in self._generator:
                data = f"data: {json.dumps({'chunk': chunk})}\n\n".encode()
                await send({"type": "http.response.body", "body": data, "more_body": True})
        finally:
            await send({"type": "http.response.body", "body": b"data: [DONE]\n\n", "more_body": False})


def _make_provider(provider_name: str, api_key: str, model: str, max_tokens: int) -> BaseProvider:
    if provider_name == "anthropic":
        from shakti.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    if provider_name == "openai":
        from shakti.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    raise ValueError(f"Unknown AI provider: {provider_name!r}. Use 'anthropic' or 'openai'.")


class AI:
    """The Shakti AI module — chat, streaming, RAG, agents, templates.

    Config keys (under ``ai:``):

    .. code-block:: yaml

        ai:
          provider: anthropic          # anthropic | openai
          model: claude-sonnet-4-6
          api_key: ${ANTHROPIC_API_KEY}
          max_tokens: 1000
          temperature: 0.7
          system_prompt: "You are a helpful assistant."
          prefix: /ai                  # route prefix (default: /ai)
    """

    def __init__(
        self,
        config: Config | None = None,
        *,
        provider: str = "anthropic",
        api_key: str = "",
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: str = "You are a helpful assistant.",
        prefix: str = "/ai",
    ) -> None:
        if config is not None:
            provider   = config.get("ai.provider", provider)
            api_key    = config.get("ai.api_key", api_key)
            model      = config.get("ai.model", model)
            max_tokens = config.get("ai.max_tokens", max_tokens, cast=int)
            temperature = config.get("ai.temperature", temperature, cast=float)
            system_prompt = config.get("ai.system_prompt", system_prompt)
            prefix = config.get("ai.prefix", prefix)

        if not api_key:
            raise ValueError("AI: api_key is required. Set ai.api_key in config or pass directly.")

        self.provider_name = provider
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.prefix = prefix

        self._provider: BaseProvider = _make_provider(provider, api_key, model, max_tokens)
        self.rag = RAGStore()
        self._templates: dict[str, PromptTemplate] = {}

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: Shakti) -> None:
        app.container.register_instance(AI, self)
        app.include_router(self._build_router(), prefix=self.prefix)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    async def chat(
        self,
        message: str,
        *,
        history: list[Message] | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Single-turn or multi-turn chat. Returns the reply text."""
        messages = [*(history or []), Message("user", message)]
        response = await self._provider.complete(
            messages,
            system=system or self.system_prompt,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        logger.debug("AI chat — %d tokens used", response.total_tokens)
        return response.content

    async def complete(
        self,
        message: str,
        *,
        history: list[Message] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Like chat() but returns the full AIResponse with token counts."""
        messages = [*(history or []), Message("user", message)]
        return await self._provider.complete(
            messages,
            system=system or self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs,
        )

    def stream(
        self,
        message: str,
        *,
        history: list[Message] | None = None,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream response chunks as an async generator."""
        messages = [*(history or []), Message("user", message)]
        return self._provider.stream(
            messages,
            system=system or self.system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def ask(self, template_name: str, **variables: Any) -> str:
        """Render a named prompt template and send to AI."""
        tpl = self._templates.get(template_name)
        if tpl is None:
            raise ValueError(f"Unknown template: {template_name!r}. Register with ai.register_template().")
        prompt = tpl.render(**variables)
        return await self.chat(prompt, system=tpl.system)

    async def rag_chat(
        self,
        question: str,
        *,
        k: int = 5,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Ask a question using retrieved context (RAG)."""
        chunks = self.rag.search(question, k=k)
        context = self.rag.build_context(chunks)
        rag_system = (system or self.system_prompt) + (
            "\n\nAnswer questions using ONLY the provided context. "
            "If the answer is not in the context, say so.\n\nContext:\n" + context
            if context else ""
        )
        answer = await self.chat(question, system=rag_system)
        return {
            "answer": answer,
            "sources": [
                {"text": c.text[:200], "score": round(c.score, 3), "metadata": c.metadata}
                for c in chunks if c.score > 0
            ],
        }

    def agent(self, *, system: str | None = None, max_iterations: int = 5) -> Agent:
        """Create a new Agent backed by this AI's provider."""
        return Agent(self._provider, system=system or self.system_prompt, max_iterations=max_iterations)

    # ------------------------------------------------------------------
    # Template registry
    # ------------------------------------------------------------------
    def register_template(self, name: str, template: PromptTemplate) -> None:
        self._templates[name] = template

    # ------------------------------------------------------------------
    # Auto routes
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _ai = self

        @router.post("/chat")
        async def chat_endpoint(body: dict) -> dict:
            """POST /ai/chat — { "message": "...", "history": [...], "system": "..." }"""
            message = body.get("message", "")
            if not message:
                raise HTTPException(422, "Missing 'message' field")
            history = [Message(**m) for m in body.get("history", [])]
            system = body.get("system")
            reply = await _ai.chat(message, history=history, system=system)
            return {"reply": reply, "model": _ai.model, "provider": _ai.provider_name}

        @router.post("/complete")
        async def complete_endpoint(body: dict) -> dict:
            """POST /ai/complete — returns full response with token counts"""
            message = body.get("message", "")
            if not message:
                raise HTTPException(422, "Missing 'message' field")
            history = [Message(**m) for m in body.get("history", [])]
            resp = await _ai.complete(message, history=history, system=body.get("system"))
            return resp.to_dict()

        @router.post("/stream")
        async def stream_endpoint(body: dict) -> SSEResponse:
            """POST /ai/stream — SSE streaming response"""
            message = body.get("message", "")
            if not message:
                raise HTTPException(422, "Missing 'message' field")
            history = [Message(**m) for m in body.get("history", [])]
            return SSEResponse(_ai.stream(message, history=history, system=body.get("system")))

        @router.post("/rag/add")
        async def rag_add(body: dict) -> dict:
            """POST /ai/rag/add — { "text": "...", "metadata": {...} }"""
            text = body.get("text", "")
            if not text:
                raise HTTPException(422, "Missing 'text' field")
            ids = _ai.rag.add(text, metadata=body.get("metadata", {}))
            return {"added_chunks": len(ids), "total_chunks": len(_ai.rag)}

        @router.post("/rag/query")
        async def rag_query(body: dict) -> dict:
            """POST /ai/rag/query — { "question": "...", "k": 5 }"""
            question = body.get("question", "")
            if not question:
                raise HTTPException(422, "Missing 'question' field")
            return await _ai.rag_chat(question, k=int(body.get("k", 5)))

        @router.get("/info")
        async def ai_info() -> dict:
            return {
                "provider": _ai.provider_name,
                "model": _ai.model,
                "max_tokens": _ai.max_tokens,
                "temperature": _ai.temperature,
                "rag_chunks": len(_ai.rag),
                "templates": list(_ai._templates.keys()),
            }

        return router

    def __repr__(self) -> str:
        return f"<AI provider={self.provider_name!r} model={self.model!r}>"
