"""Minimal Shakti example.

Run from this directory:

    uvicorn main:app --reload
"""

from shakti import Depends, Shakti, Request, Router
from shakti.middleware import RequestLoggingMiddleware

app = Shakti(title="hello-shakti")
app.add_middleware(RequestLoggingMiddleware)


async def client_info(request: Request) -> dict:
    return {"client": request.client, "user_agent": request.headers.get("user-agent")}


@app.get("/")
async def index() -> dict:
    return {"app": app.title, "routes": len(app.router.routes)}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


api = Router(prefix="/api")


@api.get("/greet/{name}")
async def greet(name: str, shout: bool = False, info: dict = Depends(client_info)) -> dict:
    message = f"Hello, {name}!"
    return {"message": message.upper() if shout else message, "info": info}


app.include_router(api)
