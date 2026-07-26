"""Shakti Document AI — PDF, image, and text processing."""

from shakti.docs.docs import DocumentAI
from shakti.docs.storage import Document, DocumentStore
from shakti.docs.extractors import extract_content, extract_pdf, extract_text

__all__ = [
    "Document",
    "DocumentAI",
    "DocumentStore",
    "extract_content",
    "extract_pdf",
    "extract_text",
]
