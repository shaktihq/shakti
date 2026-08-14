# RAG

`ai.rag` is an in-memory retrieval-augmented-generation store: add documents, then ask questions grounded in only what you've added. No external vector database required.

## How retrieval works

`RAGStore` chunks documents by word count (default 300 words, 50-word overlap) and scores query relevance with TF-IDF cosine similarity — no embeddings, no network calls, works out of the box. It's a good fit for small-to-medium document sets (comfortably up to ~10k chunks); for larger corpora or higher-quality semantic search, swap in embeddings from your provider instead (see [below](#going-beyond-tf-idf)).

## Adding documents

```python
ai.rag.add("Shakti is an AI-first, async Python web framework.", metadata={"source": "docs"})
ai.rag.add(long_document_text, metadata={"source": "handbook.pdf"})
```

`add()` splits the text into overlapping chunks and returns their generated chunk IDs. `metadata` is stored per-chunk and echoed back with search results (e.g. `source` for citations).

Or over HTTP, via the auto-mounted route:

```
POST /ai/rag/add
{"text": "...", "metadata": {"source": "docs"}}
```

## Asking grounded questions

```python
result = await ai.rag_chat("What is Shakti?")
result["answer"]    # str — the model's answer
result["sources"]   # [{"text": "...", "score": 0.83, "metadata": {...}}, ...]
```

`rag_chat()` retrieves the top-`k` (default 5) most relevant chunks, builds a context block, and instructs the model to answer *only* from that context (falling back to "not in the context" if it isn't there) — reducing hallucination compared to an unconstrained prompt. `sources` only includes chunks that actually scored above zero relevance.

Over HTTP:

```
POST /ai/rag/query
{"question": "What is Shakti?", "k": 5}
```

## Searching without asking the model

```python
chunks = ai.rag.search("async framework", k=3)   # -> list[Chunk] (id, text, metadata, score)
context = ai.rag.build_context(chunks, max_chars=2000)
```

Useful if you want the retrieved context for something other than a direct chat call (e.g. building your own prompt).

## Managing the store

```python
len(ai.rag)     # total chunk count
ai.rag.clear()  # wipe everything
```

The store is in-process memory — it doesn't persist across restarts and isn't shared across workers. For anything you need to survive a restart or scale horizontally, persist your source documents elsewhere and re-`add()` them on startup, or swap the store for a real vector DB.

## Going beyond TF-IDF

`RAGStore(chunk_size=300, overlap=50)` accepts different chunking parameters, but retrieval quality is inherently keyword-based, not semantic. For higher-quality search (paraphrases, synonyms, cross-lingual queries), replace the scoring with embeddings from your AI provider and a proper vector index — `RAGStore` is deliberately dependency-free so it works everywhere by default, not the ceiling of what you can build.
