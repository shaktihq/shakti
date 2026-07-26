# Shakti

**An AI-first, async Python web framework.**

> Flask simplicity · FastAPI performance · Django batteries · Built-in AI

```bash
pip install "shakti-framework[all]"
shakti new myapp && cd myapp && shakti run --reload
```

---

## Why Shakti?

| | Django | FastAPI | **Shakti** |
|---|---|---|---|
| Async-first | ❌ | ✅ | ✅ |
| Built-in ORM | ✅ | ❌ | ✅ |
| Admin panel | ✅ | ❌ | ✅ |
| JWT Auth | ❌ | ❌ | ✅ |
| **Built-in AI** | ❌ | ❌ | ✅ |
| WebSockets | ❌ | ✅ | ✅ |
| Background jobs | ❌ | ❌ | ✅ |
| Monitoring | ❌ | ❌ | ✅ |

---

## 60-second demo

```python
from shakti import Shakti, Depends
from shakti.config import Config
from shakti.orm import Database, Repository
from shakti.auth import Auth
from shakti.auth.models import User
from shakti.ai import AI
from shakti.admin import Admin
from shakti.monitoring import Monitor
from shakti.websocket import WebSocket

config = Config()
app = Shakti(title="My App", config=config)

db = Database(config.require("database.url"))
db.init_app(app)

auth = Auth(db, secret_key=config.require("auth.secret_key"))
auth.init_app(app)

ai = AI(config)
ai.init_app(app)

admin = Admin(db, auth)
admin.register(User)
admin.init_app(app)

monitor = Monitor()
monitor.init_app(app)

@app.get("/")
async def index() -> dict:
    return {"hello": "world"}

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

**That's it.** You now have:

- ✅ REST API with typed routing
- ✅ JWT authentication
- ✅ AI chat endpoint (Claude/OpenAI)
- ✅ WebSocket real-time chat
- ✅ Admin panel at `/admin/`
- ✅ Monitoring dashboard at `/monitor/`

---

## Install

```bash
# Core only
pip install shakti-framework

# With everything
pip install "shakti-framework[all]"

# Pick what you need
pip install "shakti-framework[server,orm,auth,ai]"
```

## CLI

```bash
shakti new myapp              # scaffold project
shakti run --reload           # start dev server
shakti generate api Post title:str body:text  # generate full CRUD
shakti makemigrations "add posts"  # create migration
shakti migrate                # apply migrations
```
