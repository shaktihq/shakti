# Shakti Demo App

A complete demo showing all Shakti features.

## Setup

```bash
pip install "shakti-framework[all]" anthropic
```

Add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

## Run

```bash
shakti makemigrations "init"
shakti migrate
shakti run main:app --reload
```

## Try it

| URL | What |
|-----|------|
| `GET /` | API overview |
| `POST /ai/chat` | AI chat |
| `POST /ai/stream` | Streaming AI |
| `ws://localhost:8000/ws/chat` | WebSocket AI |
| `http://localhost:8000/admin/` | Admin panel |
| `http://localhost:8000/monitor/` | Monitoring |

## WebSocket test (browser console)

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({message: "Hello Shakti!"}));
```
