# Shakti

**An AI-first, async Python web framework.**

> Born in India. Built for the world.

```bash
pip install "shakti-framework[all]" 
```

---

## Why Shakti?

| Feature | Django | FastAPI | **Shakti** |
|---------|--------|---------|------------|
| Async-first | ❌ | ✅ | ✅ |
| Built-in ORM | ✅ | ❌ | ✅ |
| Admin panel | ✅ | ❌ | ✅ |
| JWT Auth | ❌ | ❌ | ✅ |
| **Built-in AI** | ❌ | ❌ | ✅ |
| WebSockets | ❌ | ✅ | ✅ |
| Background Jobs | ❌ | ❌ | ✅ |
| Monitoring | ❌ | ❌ | ✅ |
| Document AI | ❌ | ❌ | ✅ |

---

## Quick Start

```bash
pip install "shakti[all]"
shakti new myapp
cd myapp
shakti run --reload
```

Visit `http://127.0.0.1:8000` — your app is live.

---

## 60-second example

```python
from shakti import Shakti, Depends
from shakti.config import Config
from shakti.orm import Database, Repository
from shakti.auth import Auth
from shakti.auth.models import User
from shakti.ai import AI
from shakti.admin import Admin
from shakti.monitoring import Monitor
from shakti.workflows import WorkflowEngine
from shakti.websocket import WebSocket

config = Config()
app = Shakti(title="My App", config=config)

db = Database(config.require("database.url"))
db.init_app(app)

auth = Auth(db, secret_key=config.require("auth.secret_key"))
auth.init_app(app)

ai = AI(config)
ai.init_app(app)

admin = Admin(db, auth, title="My Admin")
admin.register(User)
admin.init_app(app)

monitor = Monitor()
monitor.init_app(app)

workflows = WorkflowEngine()
workflows.init_app(app)

@app.get("/")
async def index() -> dict:
    return {"framework": "Shakti", "status": "running"}

@app.get("/me")
async def me(user: User = Depends(auth.get_current_user())) -> dict:
    return user.to_dict()

@app.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    async for msg in ws.iter_json():
        reply = await ai.chat(msg["text"])
        await ws.send_json({"reply": reply})
```

**One app. Everything included:**
- ✅ Async REST API
- ✅ JWT authentication
- ✅ AI chat (Claude/OpenAI)
- ✅ WebSocket real-time
- ✅ Admin panel at `/admin/`
- ✅ Monitoring at `/monitor/`
- ✅ Background jobs
- ✅ PDF/OCR document AI

---

## Install

```bash
pip install shakti                    # core only
pip install "shakti-framework[all]"        # + uvicorn
pip install "shakti[orm]"             # + SQLAlchemy
pip install "shakti[auth]"            # + JWT + bcrypt
pip install "shakti[ai]"              # + Claude/OpenAI
pip install "shakti[monitoring]"      # + psutil
pip install "shakti[all]"             # everything
```

---

## CLI

```bash
shakti new myapp                         # scaffold project
shakti run --reload                      # start dev server
shakti generate model Post title:str body:text   # generate model
shakti generate api Comment body:text    # model + full CRUD
shakti makemigrations "add posts"        # create migration
shakti migrate                           # apply migrations
shakti version                           # show version
```

---

## Configuration

```yaml
# config/settings.yaml
app:
  name: myapp
  debug: true

database:
  url: sqlite+aiosqlite:///./myapp.db

auth:
  secret_key: ${SECRET_KEY}

ai:
  provider: anthropic
  model: claude-sonnet-4-pip install "shakti-framework[all]"
  api_key: ${ANTHROPIC_API_KEY}
  system_prompt: "You are a helpful assistant."
```

---

## Modules

| Module | Import | What it does |
|--------|--------|-------------|
| Core | `from shakti import Shakti` | Routing, middleware, DI, config |
| ORM | `from shakti.orm import Database` | SQLAlchemy async + migrations |
| Auth | `from shakti.auth import Auth` | JWT, RBAC, API keys |
| AI | `from shakti.ai import AI` | Claude/OpenAI, RAG, agents |
| Admin | `from shakti.admin import Admin` | Auto-generated admin panel |
| WebSocket | `from shakti.websocket import WebSocket` | Real-time connections |
| Document AI | `from shakti.docs import DocumentAI` | PDF, OCR, document Q&A |
| Workflows | `from shakti.workflows import WorkflowEngine` | Background jobs |
| Monitoring | `from shakti.monitoring import Monitor` | Health checks, metrics |

---

## License

MIT © Aditya Bhat — Born in India 🇮🇳
