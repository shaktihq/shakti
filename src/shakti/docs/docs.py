"""DocumentAI — PDF, image, and text document processing with AI.

Usage::

    from shakti.docs import DocumentAI

    docs = DocumentAI(ai)
    docs.init_app(app)

    # Upload via API:
    # POST /docs/upload  { "filename": "report.pdf", "content": "<base64>", "content_type": "application/pdf" }
    # POST /docs/ask     { "question": "What is the total revenue?" }
    # POST /docs/extract { "doc_id": "...", "schema": {"name": "string", "date": "string"} }
    # GET  /docs/list
    # GET  /docs/{id}
    # DELETE /docs/{id}
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING, Any

from shakti.ai.rag import RAGStore
from shakti.docs.extractors import extract_content
from shakti.docs.storage import Document, DocumentStore
from shakti.exceptions import HTTPException
from shakti.routing.router import Router

if TYPE_CHECKING:
    from shakti.ai.ai import AI
    from shakti.application import Shakti


class DocumentAI:
    """AI-powered document processing — extract, query, summarize.

    Supports: PDF, PNG, JPEG, WEBP, TXT, MD, CSV.

    Documents are chunked and stored in a RAG vector store for Q&A.
    """

    def __init__(
        self,
        ai: AI,
        *,
        prefix: str = "/docs",
        chunk_size: int = 400,
        overlap: int = 60,
    ) -> None:
        self.ai = ai
        self.prefix = prefix
        self._store = DocumentStore()
        self._rag = RAGStore(chunk_size=chunk_size, overlap=overlap)

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: Shakti) -> None:
        app.container.register_instance(DocumentAI, self)
        app.include_router(self._build_router(), prefix=self.prefix)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    async def process(
        self,
        content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Extract text from a document and index it for Q&A."""
        text = await extract_content(
            content,
            filename,
            content_type,
            provider=self.ai._provider,
        )
        if not text.strip():
            raise ValueError(f"Could not extract any text from {filename!r}")

        doc_id = str(uuid.uuid4())
        meta = {**(metadata or {}), "doc_id": doc_id, "filename": filename}
        chunk_ids = self._rag.add(text, metadata=meta, source_id=doc_id)

        doc = Document(
            id=doc_id,
            filename=filename,
            content_type=content_type,
            text=text,
            chunk_ids=chunk_ids,
            metadata=metadata or {},
            char_count=len(text),
            page_count=text.count("[Page ") or 1,
        )
        self._store.add(doc)
        return doc

    async def ask(
        self,
        question: str,
        *,
        doc_id: str | None = None,
        k: int = 5,
    ) -> dict[str, Any]:
        """Ask a question across all documents (or a specific one)."""
        if not self._rag:
            return {"answer": "No documents uploaded yet.", "sources": []}

        chunks = self._rag.search(question, k=k)

        # Filter by doc_id if specified
        if doc_id:
            chunks = [c for c in chunks if c.metadata.get("doc_id") == doc_id]
            if not chunks:
                raise HTTPException(404, f"No content found for document {doc_id!r}")

        context = self._rag.build_context(chunks)
        system = (
            "You are a document analysis assistant. "
            "Answer questions using ONLY the provided document context. "
            "If the answer is not in the context, say 'This information is not in the provided documents.' "
            "Be precise and cite the source when possible.\n\n"
            f"Document context:\n{context}"
        )
        answer = await self.ai.chat(question, system=system)

        return {
            "answer": answer,
            "sources": [
                {
                    "filename": c.metadata.get("filename", "unknown"),
                    "doc_id": c.metadata.get("doc_id"),
                    "excerpt": c.text[:200] + "…" if len(c.text) > 200 else c.text,
                    "relevance_score": round(c.score, 3),
                }
                for c in chunks if c.score > 0
            ],
        }

    async def summarize(self, doc_id: str, *, style: str = "concise") -> dict[str, Any]:
        """Summarize a document."""
        doc = self._store.get(doc_id)
        if not doc:
            raise HTTPException(404, f"Document {doc_id!r} not found")

        style_prompts = {
            "concise": "Write a concise 2-3 sentence summary.",
            "detailed": "Write a detailed summary covering all main points.",
            "bullet": "Write a bullet-point summary of the key points.",
            "executive": "Write an executive summary suitable for leadership.",
        }
        instruction = style_prompts.get(style, style_prompts["concise"])

        # Use first 4000 chars to avoid token limits
        text_sample = doc.text[:4000]
        if len(doc.text) > 4000:
            text_sample += f"\n\n[Document truncated — {len(doc.text)} total characters]"

        system = f"You are an expert document summarizer. {instruction}"
        prompt = f"Document: {doc.filename}\n\n{text_sample}"
        summary = await self.ai.chat(prompt, system=system)

        return {
            "doc_id": doc_id,
            "filename": doc.filename,
            "summary": summary,
            "style": style,
            "char_count": doc.char_count,
        }

    async def extract_structured(
        self,
        doc_id: str,
        schema: dict[str, str],
    ) -> dict[str, Any]:
        """Extract structured data from a document using a field schema.

        schema example: {"company_name": "string", "total_amount": "number", "date": "string"}
        """
        doc = self._store.get(doc_id)
        if not doc:
            raise HTTPException(404, f"Document {doc_id!r} not found")

        schema_desc = "\n".join(f"  - {k} ({v})" for k, v in schema.items())
        system = (
            "You extract structured data from documents. "
            "Return ONLY a valid JSON object with the requested fields. "
            "Use null for fields not found in the document. "
            "No explanation, no markdown, just the JSON object."
        )
        prompt = (
            f"Extract these fields from the document:\n{schema_desc}\n\n"
            f"Document ({doc.filename}):\n{doc.text[:3000]}"
        )
        raw = await self.ai.chat(prompt, system=system)

        # Parse JSON response
        try:
            # Strip markdown code fences if present
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            extracted = json.loads(clean)
        except json.JSONDecodeError:
            extracted = {"raw_response": raw}

        return {
            "doc_id": doc_id,
            "filename": doc.filename,
            "extracted": extracted,
            "schema": schema,
        }

    async def classify(self, doc_id: str) -> dict[str, Any]:
        """Classify the document type using AI."""
        doc = self._store.get(doc_id)
        if not doc:
            raise HTTPException(404, f"Document {doc_id!r} not found")

        system = (
            "You classify documents. Return ONLY a JSON object with keys: "
            "'type' (string: invoice, contract, report, resume, letter, receipt, other), "
            "'confidence' (number 0-1), 'language' (string), 'summary' (string, max 20 words). "
            "No markdown, just JSON."
        )
        raw = await self.ai.chat(doc.text[:1500], system=system)
        try:
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(clean)
        except json.JSONDecodeError:
            result = {"type": "unknown", "confidence": 0, "raw": raw}

        return {"doc_id": doc_id, "filename": doc.filename, **result}

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _docs = self

        @router.get("/info")
        async def info() -> dict:
            return {
                "documents": len(_docs._store),
                "chunks": len(_docs._rag),
                "supported_types": ["application/pdf", "image/png", "image/jpeg", "image/webp", "text/plain", "text/markdown", "text/csv"],
            }

        @router.get("/list")
        async def list_docs() -> list:
            return [d.to_dict() for d in _docs._store.all()]

        @router.get("/{doc_id}")
        async def get_doc(doc_id: str) -> dict:
            doc = _docs._store.get(doc_id)
            if not doc:
                raise HTTPException(404, "Document not found")
            return {**doc.to_dict(), "text_preview": doc.text[:500]}

        @router.post("/upload")
        async def upload(body: dict) -> dict:
            """
            Upload a document.

            Body:
            {
              "filename": "report.pdf",
              "content": "<base64-encoded bytes>",
              "content_type": "application/pdf",
              "metadata": {}
            }
            """
            filename = body.get("filename", "")
            b64_content = body.get("content", "")
            content_type = body.get("content_type", "application/octet-stream")

            if not filename:
                raise HTTPException(422, "Missing 'filename'")
            if not b64_content:
                raise HTTPException(422, "Missing 'content' (base64-encoded file)")

            try:
                content = base64.b64decode(b64_content)
            except Exception:
                raise HTTPException(422, "Invalid base64 content")

            try:
                doc = await _docs.process(
                    content,
                    filename,
                    content_type,
                    metadata=body.get("metadata", {}),
                )
            except ValueError as e:
                raise HTTPException(422, str(e))

            return {
                "message": "Document processed successfully",
                "document": doc.to_dict(),
            }

        @router.post("/ask")
        async def ask(body: dict) -> dict:
            """
            Ask a question about uploaded documents.

            Body: { "question": "...", "doc_id": "<optional>", "k": 5 }
            """
            question = body.get("question", "")
            if not question:
                raise HTTPException(422, "Missing 'question'")
            return await _docs.ask(
                question,
                doc_id=body.get("doc_id"),
                k=int(body.get("k", 5)),
            )

        @router.post("/summarize")
        async def summarize(body: dict) -> dict:
            """
            Summarize a document.

            Body: { "doc_id": "...", "style": "concise|detailed|bullet|executive" }
            """
            doc_id = body.get("doc_id", "")
            if not doc_id:
                raise HTTPException(422, "Missing 'doc_id'")
            return await _docs.summarize(doc_id, style=body.get("style", "concise"))

        @router.post("/extract")
        async def extract(body: dict) -> dict:
            """
            Extract structured data.

            Body: { "doc_id": "...", "schema": {"field": "type", ...} }
            """
            doc_id = body.get("doc_id", "")
            schema = body.get("schema", {})
            if not doc_id:
                raise HTTPException(422, "Missing 'doc_id'")
            if not schema:
                raise HTTPException(422, "Missing 'schema'")
            return await _docs.extract_structured(doc_id, schema)

        @router.post("/classify")
        async def classify(body: dict) -> dict:
            """Body: { "doc_id": "..." }"""
            doc_id = body.get("doc_id", "")
            if not doc_id:
                raise HTTPException(422, "Missing 'doc_id'")
            return await _docs.classify(doc_id)

        @router.delete("/{doc_id}")
        async def delete_doc(doc_id: str) -> dict:
            if not _docs._store.delete(doc_id):
                raise HTTPException(404, "Document not found")
            return {"deleted": doc_id}

        return router
