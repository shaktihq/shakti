"""OpenAI provider (GPT-4o, GPT-4, etc.)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from shakti.ai.providers.base import AIResponse, BaseProvider, Message


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1000,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError("pip install openai") from e
        self.client = AsyncOpenAI(api_key=api_key)
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
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(m.to_dict() for m in messages)

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature,
            messages=all_messages,
            **kwargs,
        )
        return AIResponse(
            content=response.choices[0].message.content or "",
            model=self.model,
            provider=self.name,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
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
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(m.to_dict() for m in messages)

        stream = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature,
            messages=all_messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
