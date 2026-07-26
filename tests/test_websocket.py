"""WebSocket tests."""

from __future__ import annotations

import asyncio
import json

import pytest

from shakti import Shakti, WebSocket, WebSocketDisconnect
from shakti.testing import TestClient


class WSTestClient:
    """Simple WebSocket test helper."""

    def __init__(self, app, path: str) -> None:
        self.app = app
        self.path = path
        self._client_send: asyncio.Queue = asyncio.Queue()
        self._server_send: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *args):
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _run(self):
        scope = {
            "type": "websocket",
            "path": self.path,
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
        }

        async def receive():
            return await self._client_send.get()

        async def send(message):
            await self._server_send.put(message)

        await self.app(scope, receive, send)

    async def connect(self):
        await self._client_send.put({"type": "websocket.connect"})
        msg = await self._server_send.get()
        assert msg["type"] == "websocket.accept"

    async def send_text(self, text: str):
        await self._client_send.put({"type": "websocket.receive", "text": text, "bytes": None})

    async def send_json(self, data):
        await self.send_text(json.dumps(data))

    async def receive(self) -> dict:
        return await asyncio.wait_for(self._server_send.get(), timeout=2.0)

    async def receive_text(self) -> str:
        msg = await self.receive()
        return msg.get("text", "")

    async def receive_json(self):
        return json.loads(await self.receive_text())

    async def disconnect(self, code: int = 1000):
        await self._client_send.put({"type": "websocket.disconnect", "code": code})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_websocket_echo():
    app = Shakti()

    @app.websocket("/ws/echo")
    async def echo(ws: WebSocket) -> None:
        await ws.accept()
        async for msg in ws.iter_text():
            await ws.send_text(f"echo: {msg}")

    async def run():
        async with WSTestClient(app, "/ws/echo") as client:
            await client.connect()
            await client.send_text("hello")
            reply = await client.receive_text()
            assert reply == "echo: hello"
            await client.send_text("shakti")
            reply2 = await client.receive_text()
            assert reply2 == "echo: shakti"
            await client.disconnect()

    asyncio.run(run())


def test_websocket_json():
    app = Shakti()

    @app.websocket("/ws/json")
    async def json_ws(ws: WebSocket) -> None:
        await ws.accept()
        async for msg in ws.iter_json():
            await ws.send_json({"received": msg["value"], "doubled": msg["value"] * 2})

    async def run():
        async with WSTestClient(app, "/ws/json") as client:
            await client.connect()
            await client.send_json({"value": 5})
            reply = await client.receive_json()
            assert reply == {"received": 5, "doubled": 10}
            await client.disconnect()

    asyncio.run(run())


def test_websocket_path_params():
    app = Shakti()
    received_params = {}

    @app.websocket("/ws/room/{room_id:int}")
    async def room_ws(ws: WebSocket) -> None:
        await ws.accept()
        received_params["room_id"] = ws.path_params.get("room_id")
        await ws.send_json({"joined": ws.path_params.get("room_id")})
        await client_ref[0].disconnect()

    client_ref = [None]

    async def run():
        async with WSTestClient(app, "/ws/room/42") as client:
            client_ref[0] = client
            await client.connect()
            reply = await client.receive_json()
            assert reply["joined"] == 42
            assert received_params["room_id"] == 42

    asyncio.run(run())


def test_websocket_not_found():
    app = Shakti()

    async def run():
        scope = {
            "type": "websocket",
            "path": "/ws/nonexistent",
            "query_string": b"",
            "headers": [],
            "client": ("test", 1),
        }
        messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(msg):
            messages.append(msg)

        await app(scope, receive, send)
        assert any(m.get("code") == 4004 for m in messages)

    asyncio.run(run())


def test_websocket_chat_broadcast():
    """Test multi-message conversation."""
    app = Shakti()
    history = []

    @app.websocket("/ws/history")
    async def history_ws(ws: WebSocket) -> None:
        await ws.accept()
        async for msg in ws.iter_text():
            history.append(msg)
            await ws.send_json({"total": len(history), "last": msg})

    async def run():
        async with WSTestClient(app, "/ws/history") as client:
            await client.connect()
            for word in ["one", "two", "three"]:
                await client.send_text(word)
                reply = await client.receive_json()
                assert reply["last"] == word
            assert len(history) == 3
            await client.disconnect()

    asyncio.run(run())


def test_websocket_with_http_routes():
    """WebSocket and HTTP routes coexist."""
    app = Shakti()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text("connected")
        await websocket.close()

    # HTTP still works
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200

    # WebSocket works
    async def run():
        async with WSTestClient(app, "/ws") as wsclient:
            await wsclient.connect()
            msg = await wsclient.receive_text()
            assert msg == "connected"

    asyncio.run(run())
