---
title: Build an AI Agent with Shakti
description: Tutorial — build a tool-calling AI agent in Python with Shakti Python Framework, using Anthropic's tool use API.
---

# Build an AI Agent with Shakti

An AI agent — a model that can call functions you define and use the results to answer a question — is a few lines of code with Shakti's built-in [`Agent`](../ai/agents.md). This builds one that can check order status from your own database.

## Set up AI

```python
from shakti import AI

ai = AI(config)  # ai.provider: anthropic in config/settings.yaml
ai.init_app(app)
```

Agents currently require the Anthropic provider, since they're built on Anthropic's tool-use API — see [Agents](../ai/agents.md#provider-support).

## Define a tool

A tool is just an async function with a docstring. Shakti generates the tool schema the model needs from the function signature automatically:

```python
from shakti.orm import Database, Repository
from app.models.order import Order

agent = ai.agent(system="You are a helpful order-status assistant.")

@agent.tool(description="Look up an order's status by order ID")
async def get_order_status(order_id: int) -> str:
    async with db.session() as session:
        order = await session.get(Order, order_id)
    if order is None:
        return f"No order found with ID {order_id}"
    return f"Order {order_id} is {order.status}"
```

## Wire it up as an endpoint

```python
@app.post("/support/ask")
async def ask_support(body: dict) -> dict:
    result = await agent.run(body["question"])
    return {
        "answer": result.content,
        "tool_calls": [tc.tool_name for tc in result.tool_calls],
    }
```

## Try it

```bash
curl -X POST http://127.0.0.1:8000/support/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the status of order 42?"}'
```

The model decides whether it needs to call `get_order_status`, calls it with the order ID it extracted from the question, and uses the result to answer in natural language — the loop (call the model, run any tool it asks for, feed the result back, repeat) is handled for you, up to `max_iterations` round-trips.

## Multiple tools compose naturally

Register more `@agent.tool`-decorated functions and the model chooses which ones it needs for a given question — you don't have to route the request to the right tool yourself:

```python
@agent.tool(description="Check current inventory for a product SKU")
async def check_inventory(sku: str) -> str:
    ...

@agent.tool(description="Look up a customer's shipping address")
async def get_shipping_address(customer_id: int) -> str:
    ...
```

A question like "is order 42's product in stock, and where is it shipping?" can trigger both tools in one `agent.run()` call.

## Going further

- Ground the agent's answers in your own documents with [RAG](../ai/rag.md) instead of (or alongside) tool calls
- Stream the response token-by-token with [Streaming](../ai/streaming.md)
- Reuse the same pattern to build internal ops tools, not just customer-facing chat
