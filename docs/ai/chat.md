# Chat & Completion

## Simple chat

```python
@app.post("/chat")
async def chat(body: dict) -> dict:
    reply = await ai.chat(body["message"])
    return {"reply": reply}
```

`ai.chat(message, *, history=None, system=None, temperature=None, max_tokens=None)` returns just the reply text (`str`). `temperature`/`max_tokens` default to the values configured on `AI`; pass them per-call to override.

## Multi-turn conversations

Pass prior turns as `history` — a list of `Message(role, content)`:

```python
from shakti.ai.providers.base import Message

@app.post("/converse")
async def converse(body: dict) -> dict:
    history = [Message(**m) for m in body.get("history", [])]
    reply = await ai.chat(body["message"], history=history)
    return {"reply": reply}
```

`role` is `"user"`, `"assistant"`, or `"system"`. The auto-mounted `POST /ai/chat` route does exactly this, accepting `history` as a list of `{"role": ..., "content": ...}` dicts in the request body.

## Full response with token counts

`ai.chat()` throws away everything but the text. Use `ai.complete()` when you need usage data:

```python
response = await ai.complete("Summarize this document")
response.content         # str
response.model           # str
response.provider        # "anthropic" | "openai"
response.input_tokens    # int
response.output_tokens   # int
response.total_tokens    # property: input + output
response.to_dict()       # {"content", "model", "provider", "tokens": {"input", "output", "total"}}
```

This is exactly what `POST /ai/complete` returns.

## Per-call overrides

```python
reply = await ai.chat(
    "Be creative",
    system="You are a poet.",
    temperature=1.0,
    max_tokens=200,
)
```

`system` overrides the configured `ai.system_prompt` for just this call — handy for role-specific endpoints without instantiating a second `AI`.

## Errors

The auto-mounted routes validate the request body and raise `422` if `message` (or `question`, for RAG) is missing. Provider-level errors (bad API key, rate limits, network failures) propagate as whatever exception the underlying SDK raises — wrap calls in your own `try/except` (or an [exception handler](../core/request-response.md#custom-exception-handlers)) if you want a specific HTTP status for those.

See [Streaming](streaming.md) for token-by-token output, [RAG](rag.md) for grounding answers in your own documents, and [Prompt Templates](templates.md) for reusable prompts via `ai.ask()`.
