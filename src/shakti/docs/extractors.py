"""Text extractors for PDF, images, plain text, and markdown."""

from __future__ import annotations

import base64
import io
from typing import Any


async def extract_pdf(content: bytes) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        import pypdf
    except ImportError as e:
        raise RuntimeError("pip install pypdf") from e

    reader = pypdf.PdfReader(io.BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i}]\n{text.strip()}")
    return "\n\n".join(pages)


async def extract_image_ocr(content: bytes, media_type: str, provider: Any) -> str:
    """Use Claude vision to OCR an image — no Tesseract needed."""
    from shakti.ai.providers.anthropic_provider import AnthropicProvider

    if not isinstance(provider, AnthropicProvider):
        raise RuntimeError("Image OCR requires Anthropic provider.")

    b64 = base64.standard_b64encode(content).decode()
    response = await provider.client.messages.create(
        model=provider.model,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {"type": "text", "text": "Extract ALL text from this image exactly as it appears. Return only the extracted text, no commentary."},
            ],
        }],
    )
    return response.content[0].text


async def extract_text(content: bytes, encoding: str = "utf-8") -> str:
    """Decode plain text / markdown files."""
    return content.decode(encoding, errors="replace")


async def extract_content(
    content: bytes,
    filename: str,
    content_type: str,
    provider: Any | None = None,
) -> str:
    """Route to the correct extractor based on content_type / filename."""
    ct = content_type.lower()
    name = filename.lower()

    if ct == "application/pdf" or name.endswith(".pdf"):
        return await extract_pdf(content)

    if ct.startswith("image/") or any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
        if provider is None:
            raise RuntimeError("Image OCR requires an AI provider.")
        return await extract_image_ocr(content, ct or "image/jpeg", provider)

    if ct in ("text/plain", "text/markdown", "text/csv") or any(
        name.endswith(ext) for ext in (".txt", ".md", ".csv", ".rst")
    ):
        return await extract_text(content)

    # Default: try as text
    return await extract_text(content)
