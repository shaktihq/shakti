"""Shakti Demo App — shows all framework features in one app.

Run:
    pip install "shakti-framework[all]"
    pip install anthropic
    cd examples/demo_app
    shakti makemigrations "init"
    shakti migrate
    shakti run main:app --reload

Then open:
    http://localhost:8000/          → REST API
    http://localhost:8000/admin/    → Admin panel
    http://localhost:8000/monitor/  → Monitoring dashboard
    ws://localhost:8000/ws/chat     → WebSocket AI chat
"""

from shakti import Depends, Shakti
from shakti.config import Config
from shakti.orm import Base, Database, Repository
from shakti.auth import Auth
from shakti.auth.models import User
from shakti.admin import Admin
from shakti.ai import AI
from shakti.docs import DocumentAI
from shakti.monitoring import Monitor
from shakti.workflows import WorkflowEngine
from shakti.websocket import WebSocket

from app.models.message import Message

# ─── Setup ────────────────────────────────────────────────────────────────────

config = Config()
app = Shakti(title="Shakti Demo", config=config)

db = Database(config.require("database.url"))
db.init_app(app)

auth = Auth(db, secret_key=config.require("auth.secret_key"))
auth.init_app(app)

ai = AI(config)
ai.init_app(app)

docs_ai = DocumentAI(ai)
docs_ai.init_app(app)

workflows = WorkflowEngine(workers=2)
workflows.init_app(app)

monitor = Monitor(title="Shakti Demo Monitor")
monitor.init_app(app)

admin = Admin(db, auth, title="Shakti Demo Admin")
admin.register(User,    list_fields=["id", "email", "username", "role", "is_active"],
                        search_fields=["email", "username"])
admin.register(Message, list_fields=["id", "role", "content", "created_at"],
                        search_fields=["content"])
admin.init_app(app)


# ─── Startup: create tables ───────────────────────────────────────────────────

@app.on_startup
async def create_tables() -> None:
    await db.create_all(Base)


# ─── Background job ──────────────────────────────────────────────────────────

@workflows.job
async def log_message(content: str, role: str) -> str:
    """Save a chat message to the database."""
    async with db.session() as session:
        msg = Message(role=role, content=content)
        session.add(msg)
        await session.commit()
    return f"saved {role} message"


@monitor.health_check("database")
async def check_db() -> str:
    async with db.session() as session:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
    return "connected"


# ─── HTTP Routes ─────────────────────────────────────────────────────────────

@app.get("/")
async def index() -> dict:
    return {
        "app": "Shakti Demo",
        "version": "0.1.0",
        "endpoints": {
            "REST API":   "GET/POST /api/*",
            "AI Chat":    "POST /ai/chat",
            "AI Stream":  "POST /ai/stream",
            "WebSocket":  "ws://localhost:8000/ws/chat",
            "Admin":      "http://localhost:8000/admin/",
            "Monitor":    "http://localhost:8000/monitor/",
            "Docs AI":    "POST /docs/upload",
        },
    }


@app.get("/api/messages")
async def list_messages() -> list:
    async with db.session() as session:
        repo = Repository(Message, session)
        messages = await repo.all()
        return [m.to_dict() for m in messages]


@app.post("/api/messages")
async def create_message(body: dict) -> dict:
    async with db.session() as session:
        repo = Repository(Message, session)
        msg = await repo.create(role=body.get("role", "user"), content=body["content"])
        await session.commit()
        return msg.to_dict()


@app.get("/api/me")
async def me(user: User = Depends(auth.get_current_user())) -> dict:
    return user.to_dict()


# ─── WebSocket AI Chat ────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    """Real-time AI chat over WebSocket.

    Send: {"message": "Hello!"}
    Receive: {"type": "chunk", "content": "Hi..."} (streaming)
             {"type": "done"}
    """
    await ws.accept()
    await ws.send_json({"type": "connected", "message": "Connected to Shakti AI Chat"})

    async for data in ws.iter_json():
        message = data.get("message", "")
        if not message:
            continue

        # Stream AI response token by token
        full_response = []
        async for chunk in ai.stream(message):
            full_response.append(chunk)
            await ws.send_json({"type": "chunk", "content": chunk})

        await ws.send_json({"type": "done"})

        # Save to DB in background
        await workflows.enqueue(
            log_message,
            content=message,
            role="user",
        )
        await workflows.enqueue(
            log_message,
            content="".join(full_response),
            role="assistant",
        )
