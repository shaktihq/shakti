"""Anthropic Claude provider."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from shakti.ai.providers.base import AIResponse, BaseProvider, Message


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1000,
    ) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ImportError("pip install anthropic") from e
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.default_max_tokens = max_tokens

    async def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AIResponse:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature,
            system=system or "",
            messages=[m.to_dict() for m in messages],
            **kwargs,
        )
        return AIResponse(
            content=response.content[0].text,
            model=self.model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature,
            system=system or "",
            messages=[m.to_dict() for m in messages],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            system=system or "",
            tools=tools,
            messages=[m.to_dict() for m in messages],
            **kwargs,
        )
        return {
            "stop_reason": response.stop_reason,
            "content": response.content,
            "usage": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        }
