"""WebSocket support for Shakti."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from shakti.datastructures import Headers, QueryParams, State
from shakti.types import Receive, Scope, Send


class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000) -> None:
        self.code = code
        super().__init__(f"WebSocket disconnected with code {code}")


class WebSocket:
    """Represents a live WebSocket connection.

    Usage::

        @app.websocket("/ws/chat")
        async def chat(ws: WebSocket) -> None:
            await ws.accept()
            async for message in ws.iter_json():
                reply = await ai.chat(message["text"])
                await ws.send_json({"reply": reply})
    """

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.scope = scope
        self._receive = receive
        self._send = send
        self.path = scope.get("path", "/")
        self.headers = Headers(scope.get("headers", []))
        self.query_params = QueryParams(scope.get("query_string", b""))
        self.path_params: dict[str, Any] = {}
        self.state = State()
        self._accepted = False

    @property
    def client(self) -> tuple[str, int] | None:
        return self.scope.get("client")

    async def accept(self, subprotocol: str | None = None) -> None:
        """Accept the WebSocket connection."""
        if not self._accepted:
            # Consume the connect message
            message = await self._receive()
            if message["type"] != "websocket.connect":
                raise RuntimeError(f"Expected websocket.connect, got {message['type']}")
            await self._send({"type": "websocket.accept", "subprotocol": subprotocol})
            self._accepted = True

    async def send_text(self, data: str) -> None:
        await self._send({"type": "websocket.send", "text": data, "bytes": None})

    async def send_bytes(self, data: bytes) -> None:
        await self._send({"type": "websocket.send", "bytes": data, "text": None})

    async def send_json(self, data: Any) -> None:
        await self.send_text(json.dumps(data, default=str))

    async def receive_text(self) -> str:
        message = await self._receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        return message.get("text") or ""

    async def receive_bytes(self) -> bytes:
        message = await self._receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        return message.get("bytes") or b""

    async def receive_json(self) -> Any:
        text = await self.receive_text()
        return json.loads(text)

    async def iter_text(self) -> AsyncIterator[str]:
        """Yield text messages until the client disconnects."""
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            return

    async def iter_json(self) -> AsyncIterator[Any]:
        """Yield JSON messages until the client disconnects."""
        async for text in self.iter_text():
            try:
                yield json.loads(text)
            except json.JSONDecodeError:
                continue

    async def close(self, code: int = 1000, reason: str = "") -> None:
        await self._send({"type": "websocket.close", "code": code, "reason": reason})

    def __repr__(self) -> str:
        return f"<WebSocket path={self.path!r} accepted={self._accepted}>"
