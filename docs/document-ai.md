---
description: Document AI in Shakti Python Framework — PDF and image extraction, document Q&A, summarization, and structured data extraction.
---

# Document AI

`DocumentAI` handles uploading, indexing, querying, summarizing, extracting from, and classifying documents (PDF, images, text) — built on the same [RAG store](ai/rag.md) as the AI module, plus vision-capable extraction for images.

Supported types: PDF, PNG, JPEG, WEBP, TXT, MD, CSV.

## Setup

```python
from shakti import AI, DocumentAI

ai = AI(config)
ai.init_app(app)

docs = DocumentAI(ai, prefix="/docs", chunk_size=400, overlap=60)
docs.init_app(app)
```

`DocumentAI` needs an `AI` instance (it uses it both for extraction from images and for answering questions). `init_app` registers it in the DI container and mounts routes under `prefix` (default `/docs`).

## Uploading a document

```python
POST /docs/upload
{
  "filename": "report.pdf",
  "content": "<base64-encoded bytes>",
  "content_type": "application/pdf",
  "metadata": {}
}
```

Or from Python:

```python
doc = await docs.process(file_bytes, "report.pdf", "application/pdf")
doc.id            # str, use for ask/summarize/extract/classify
doc.char_count
doc.page_count
```

Text is extracted (PDFs via `pypdf`, images via the AI provider's vision capability), chunked, and indexed into an internal RAG store — same chunking/retrieval mechanics as [`ai.rag`](ai/rag.md), but scoped to `DocumentAI`'s own store rather than shared with general chat. Raises `422` (`ValueError` → `HTTPException`) if no text could be extracted at all.

## Asking questions

```python
POST /docs/ask
{"question": "What is the total revenue?", "doc_id": "<optional>", "k": 5}
```

```python
result = await docs.ask("What is the total revenue?")
result["answer"]
result["sources"]   # [{filename, doc_id, excerpt, relevance_score}, ...]
```

Without `doc_id`, it searches across *all* uploaded documents. With `doc_id`, it's scoped to just that one (raises `404` if nothing matches that filter). The system prompt instructs the model to answer only from the retrieved context, saying so explicitly when the answer isn't there.

## Summarizing

```python
POST /docs/summarize
{"doc_id": "...", "style": "concise"}   # concise | detailed | bullet | executive
```

Summarizes from the first ~4000 characters of the document (noting truncation in the prompt if the document is longer).

## Structured extraction

```python
POST /docs/extract
{"doc_id": "...", "schema": {"company_name": "string", "total_amount": "number", "date": "string"}}
```

```python
result = await docs.extract_structured(doc_id, {"invoice_number": "string", "total": "number"})
result["extracted"]   # dict matching your schema, null for fields not found
```

The model is instructed to return only JSON; if parsing fails, you get back `{"raw_response": "..."}` instead of a crash — check for that key if you need to detect a malformed extraction.

## Classification

```python
POST /docs/classify
{"doc_id": "..."}
```

Returns `{doc_id, filename, type, confidence, language, summary}` — `type` is one of `invoice`, `contract`, `report`, `resume`, `letter`, `receipt`, `other`.

## Managing documents

| Route | Does |
|---|---|
| `GET /docs/info` | document/chunk counts, supported types |
| `GET /docs/list` | all documents |
| `GET /docs/{doc_id}` | one document + a 500-char text preview |
| `DELETE /docs/{doc_id}` | remove a document |

Like the RAG store it's built on, `DocumentAI`'s document store is in-process memory — it doesn't persist across restarts. Re-upload documents on startup if you need them to survive a redeploy, or persist the original files elsewhere and re-`process()` them.
