---
description: Build AI agents with Shakti Python Framework — tool-calling agents backed by Anthropic's tool use API, with auto-generated tool schemas.
---

# Agents

`Agent` gives the model tools it can call — Python functions it decides to invoke, with results fed back in, looping until it produces a final answer. Currently backed by Anthropic's tool-use API specifically.

## Defining tools

```python
agent = ai.agent()

@agent.tool(description="Get current weather for a city")
async def get_weather(city: str) -> str:
    return f"Weather in {city}: 25°C, sunny"

result = await agent.run("What's the weather in London and Paris?")
print(result.content)
```

`@agent.tool` (usable bare or as `@agent.tool(description=...)`) registers the function and auto-generates its Anthropic tool schema from the function signature — parameter names, types (`str`/`int`/`float`/`bool`/`list`/`dict` → JSON Schema types), and which parameters are required (no default = required). If you omit `description`, the function's docstring is used.

Tool functions can be sync or async — both are supported, and exceptions inside a tool are caught and returned to the model as a `"Tool error: ..."` string rather than crashing the agent loop.

## Creating an agent

```python
agent = ai.agent(system="You are a helpful assistant with access to tools.", max_iterations=5)
```

`ai.agent()` creates an `Agent` backed by the same provider/config as your `AI` instance. `max_iterations` caps how many tool-call round-trips the loop will make before giving up (default 5) — if it's hit without a final answer, `result.content` is `"Max iterations reached without final answer."`.

## Running it

```python
result = await agent.run("What's the weather in London?", history=None)

result.content         # str — the final answer
result.tool_calls       # list[ToolResult] — every tool invocation made along the way
result.iterations       # int — how many round-trips it took
result.input_tokens     # int
result.output_tokens    # int
```

Each `ToolResult` has `tool_name`, `tool_use_id`, and `result` (whatever your function returned, stringified when sent back to the model).

## How the loop works

1. Send the conversation + registered tool schemas to the model.
2. If the model responds with text (not a tool call), that's the final answer — return it.
3. If the model calls one or more tools, run each handler, append the results as a `tool_result` message, and go back to step 1.
4. Stop after `max_iterations` if no final answer was reached.

## Provider support

`Agent` currently requires an Anthropic provider — if `ai.provider` is `"openai"`, `agent.run()` falls back to a plain `complete()` call with no tool support (tools you registered are silently ignored). Use `provider: anthropic` in config if you need tool-calling.

See [Chat & Completion](chat.md) for non-tool-calling use, and [RAG](rag.md) if what you actually need is grounding in documents rather than arbitrary function calls.
