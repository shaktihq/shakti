---
description: WebSockets in Shakti Python Framework — real-time connections with JSON messaging, path parameters, and AI streaming support.
---

# WebSockets

Shakti has built-in WebSocket support using the ASGI WebSocket protocol.

## Basic usage

```python
from shakti.websocket import WebSocket

@app.websocket("/ws/echo")
async def echo(ws: WebSocket) -> None:
    await ws.accept()
    async for message in ws.iter_text():
        await ws.send_text(f"echo: {message}")
```

## JSON messages

```python
@app.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    async for data in ws.iter_json():
        reply = await ai.chat(data["message"])
        await ws.send_json({"reply": reply})
```

## Path parameters

```python
@app.websocket("/ws/room/{room_id:int}")
async def room(ws: WebSocket) -> None:
    room_id = ws.path_params["room_id"]
    await ws.accept()
    await ws.send_json({"joined": room_id})
    async for msg in ws.iter_json():
        await ws.send_json({"room": room_id, "message": msg})
```

## AI Streaming via WebSocket

```python
@app.websocket("/ws/ai-stream")
async def ai_stream(ws: WebSocket) -> None:
    await ws.accept()
    async for data in ws.iter_json():
        # Stream tokens in real-time
        async for chunk in ai.stream(data["message"]):
            await ws.send_json({"type": "chunk", "content": chunk})
        await ws.send_json({"type": "done"})
```

## Browser client

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onopen = () => {
    ws.send(JSON.stringify({ message: "Hello Shakti!" }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.reply);
};
```

## WebSocket API

| Method | Description |
|--------|-------------|
| `await ws.accept()` | Accept the connection |
| `await ws.send_text(str)` | Send text |
| `await ws.send_json(dict)` | Send JSON |
| `await ws.send_bytes(bytes)` | Send binary |
| `await ws.receive_text()` | Receive text |
| `await ws.receive_json()` | Receive JSON |
| `async for msg in ws.iter_text()` | Stream text messages |
| `async for msg in ws.iter_json()` | Stream JSON messages |
| `await ws.close(code)` | Close connection |
| `ws.path_params` | URL path parameters |
| `ws.headers` | Request headers |
| `ws.query_params` | Query string parameters |
