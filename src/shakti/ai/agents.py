"""AI Agents — function/tool calling with Anthropic's tool use API.

Usage::

    from shakti.ai.agents import Agent

    agent = Agent(provider)

    @agent.tool(description="Get current weather for a city")
    async def get_weather(city: str) -> str:
        return f"Weather in {city}: 25°C, sunny"

    result = await agent.run("What's the weather in London and Paris?")
    print(result.content)
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any, get_type_hints

from shakti.ai.providers.base import AIResponse, Message


_PY_TO_JSON_TYPE = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}


def _build_tool_schema(func: Callable, description: str) -> dict[str, Any]:
    """Auto-generate Anthropic tool schema from function signature."""
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        py_type = hints.get(name, str).__name__ if hasattr(hints.get(name, str), "__name__") else "str"
        json_type = _PY_TO_JSON_TYPE.get(py_type, "string")
        properties[name] = {"type": json_type, "description": name.replace("_", " ")}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "name": func.__name__,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


@dataclass
class ToolResult:
    tool_name: str
    tool_use_id: str
    result: Any


@dataclass
class AgentResult:
    content: str
    tool_calls: list[ToolResult] = field(default_factory=list)
    iterations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class Agent:
    """Tool-calling AI agent backed by a provider (currently Anthropic only)."""

    def __init__(
        self,
        provider: Any,  # AnthropicProvider
        *,
        system: str | None = None,
        max_iterations: int = 5,
    ) -> None:
        self.provider = provider
        self.system = system or "You are a helpful assistant with access to tools. Use them when needed."
        self.max_iterations = max_iterations
        self._tools: dict[str, dict] = {}          # name → schema
        self._handlers: dict[str, Callable] = {}    # name → func

    def tool(
        self,
        func: Callable | None = None,
        *,
        description: str = "",
    ) -> Any:
        """Register a function as an agent tool.

        Can be used as ``@agent.tool`` or ``@agent.tool(description="…")``
        """
        def decorator(f: Callable) -> Callable:
            desc = description or (f.__doc__ or f.__name__).strip()
            schema = _build_tool_schema(f, desc)
            self._tools[f.__name__] = schema
            self._handlers[f.__name__] = f
            return f

        if func is not None:
            return decorator(func)
        return decorator

    async def _call_tool(self, name: str, inputs: dict[str, Any]) -> Any:
        handler = self._handlers.get(name)
        if handler is None:
            return f"Error: unknown tool '{name}'"
        try:
            result = handler(**inputs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as e:
            return f"Tool error: {e}"

    async def run(
        self,
        user_message: str,
        *,
        history: list[Message] | None = None,
    ) -> AgentResult:
        """Run the agent until it produces a final answer or hits max_iterations."""
        from shakti.ai.providers.anthropic_provider import AnthropicProvider

        if not isinstance(self.provider, AnthropicProvider):
            # Fallback: just complete without tools
            resp = await self.provider.complete(
                [*(history or []), Message("user", user_message)],
                system=self.system,
            )
            return AgentResult(content=resp.content, input_tokens=resp.input_tokens, output_tokens=resp.output_tokens)

        messages: list[dict] = [m.to_dict() for m in (history or [])]
        messages.append({"role": "user", "content": user_message})
        tools = list(self._tools.values())
        tool_calls: list[ToolResult] = []
        total_in = total_out = 0

        for iteration in range(self.max_iterations):
            raw = await self.provider.complete_with_tools(
                [Message(**m) for m in messages],
                tools=tools,
                system=self.system,
            )
            total_in += raw["usage"]["input"]
            total_out += raw["usage"]["output"]

            # Build assistant message content
            assistant_content = raw["content"]
            messages.append({"role": "assistant", "content": assistant_content})

            if raw["stop_reason"] != "tool_use":
                # Extract text from content blocks
                final_text = ""
                for block in assistant_content:
                    if hasattr(block, "type") and block.type == "text":
                        final_text += block.text
                    elif isinstance(block, dict) and block.get("type") == "text":
                        final_text += block.get("text", "")
                return AgentResult(
                    content=final_text,
                    tool_calls=tool_calls,
                    iterations=iteration + 1,
                    input_tokens=total_in,
                    output_tokens=total_out,
                )

            # Process tool calls
            tool_results = []
            for block in assistant_content:
                block_type = block.type if hasattr(block, "type") else block.get("type")
                if block_type == "tool_use":
                    tool_id = block.id if hasattr(block, "id") else block.get("id")
                    tool_name = block.name if hasattr(block, "name") else block.get("name")
                    tool_input = block.input if hasattr(block, "input") else block.get("input", {})
                    result = await self._call_tool(tool_name, tool_input)
                    tool_calls.append(ToolResult(tool_name=tool_name, tool_use_id=tool_id, result=result))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result),
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        return AgentResult(
            content="Max iterations reached without final answer.",
            tool_calls=tool_calls,
            iterations=self.max_iterations,
            input_tokens=total_in,
            output_tokens=total_out,
        )
