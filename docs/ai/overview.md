# AI Overview

`AI` is Shakti's built-in module for chat, streaming, RAG, prompt templates, and tool-calling agents — backed by Anthropic or OpenAI. It's a first-class citizen, not a bolt-on: one object gives you both a Python API and a set of ready-made HTTP routes.

## Setup

```yaml
# config/settings.yaml
ai:
  provider: anthropic          # anthropic | openai
  model: claude-sonnet-4-6
  api_key: ${ANTHROPIC_API_KEY}
  max_tokens: 1000
  temperature: 0.7
  system_prompt: "You are a helpful assistant."
  prefix: /ai                  # route prefix (default: /ai)
```

```python
from shakti import AI

ai = AI(config)
ai.init_app(app)
```

Or configure directly in code without YAML:

```python
ai = AI(provider="anthropic", api_key="sk-...", model="claude-sonnet-4-6")
```

`init_app` registers `AI` in the DI container and mounts the routes below under `prefix`.

## Auto-mounted routes

| Route | Body | Does |
|---|---|---|
| `POST /ai/chat` | `{message, history?, system?}` | single reply, `{reply, model, provider}` |
| `POST /ai/complete` | `{message, history?, system?}` | full response incl. token counts |
| `POST /ai/stream` | `{message, history?, system?}` | Server-Sent Events stream |
| `POST /ai/rag/add` | `{text, metadata?}` | add a document to the RAG store |
| `POST /ai/rag/query` | `{question, k?}` | RAG-grounded answer + sources |
| `GET /ai/info` | — | provider/model/config summary |

These exist so a frontend can hit `/ai/chat` directly with no backend code at all, but you're not limited to them — call `ai.chat()`/`ai.stream()`/etc. from your own handlers too.

## Python API at a glance

```python
reply = await ai.chat("Explain async/await")               # -> str
response = await ai.complete("Explain async/await")         # -> AIResponse (with token counts)
async for chunk in ai.stream("Explain async/await"):        # -> AsyncIterator[str]
    ...
answer = await ai.rag_chat("What does Shakti do?")          # -> {"answer": ..., "sources": [...]}
agent = ai.agent()                                            # -> Agent, for tool-calling
```

See the dedicated pages for each: [Chat & Completion](chat.md), [Streaming](streaming.md), [RAG](rag.md), [Agents](agents.md), [Prompt Templates](templates.md).

## Providers

Two built-in providers, selected by `ai.provider` (`"anthropic"` or `"openai"`). Both implement the same `complete()`/`stream()` interface, so switching providers is a config change, not a code change — as long as you're not using [Agents](agents.md), which currently require Anthropic's tool-use API specifically.

Install the extra you need:

```bash
pip install "shakti-framework[ai]"   # anthropic + openai clients
```
