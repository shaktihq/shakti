---
description: Streaming AI responses in Shakti Python Framework with Server-Sent Events — token-by-token output for chat interfaces.
---

# Streaming

`ai.stream()` returns an async generator of text chunks as they arrive from the provider — no need to buffer the whole reply before showing anything.

## Python API

```python
async for chunk in ai.stream("Write a short story"):
    print(chunk, end="", flush=True)
```

Signature: `ai.stream(message, *, history=None, system=None)` — same `history`/`system` semantics as [`ai.chat()`](chat.md).

## Server-Sent Events over HTTP

`SSEResponse` wraps an async chunk generator into an SSE response, which is exactly what the auto-mounted `POST /ai/stream` route does:

```python
from shakti import SSEResponse

@app.post("/stream")
async def stream_endpoint(body: dict) -> SSEResponse:
    return SSEResponse(ai.stream(body["message"]))
```

Each chunk is sent as `data: {"chunk": "..."}\n\n`; the stream ends with `data: [DONE]\n\n`. Response headers are set for you: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no` (so reverse proxies like nginx don't buffer the stream), and `Access-Control-Allow-Origin: *`.

## Consuming it from the browser

```javascript
const es = new EventSource("/ai/stream", { method: "POST" }); // or fetch() + ReadableStream
```

Since `EventSource` doesn't support `POST` bodies directly, most frontends instead use `fetch()` with a `ReadableStream` reader:

```javascript
const res = await fetch("/ai/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Hello" }),
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // parse out "data: {...}" lines
}
```

## When to use `complete()` instead

If you just need the final answer (no incremental UI), use [`ai.complete()`](chat.md#full-response-with-token-counts) — it's simpler and gives you token counts, which streaming doesn't expose per-chunk.
