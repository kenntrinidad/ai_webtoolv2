"""Document text extraction, cleanup, and chunking for the RAG ingestion pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.loaders.base import LoadedPage
from app.loaders.docx_loader import load_docx_document
from app.loaders.pdf_loader import load_pdf_document
from app.loaders.text_loader import load_text_document


class DocumentParsingError(RuntimeError):
    """Raised when a stored document cannot be converted into usable text."""


@dataclass(frozen=True)
class DocumentChunk:
    """Cleaned source text ready to be embedded in the next phase."""

    content: str
    chunk_index: int
    page_number: int | None


def clean_text(text: str) -> str:
    """Normalize whitespace while retaining paragraph boundaries for semantic chunks."""
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_pages(file_path: str | Path, file_type: str) -> list[LoadedPage]:
    """Dispatch extraction to an extensible loader based on stored file type."""
    path = Path(file_path)
    try:
        match file_type.lower().lstrip("."):
            case "pdf":
                return load_pdf_document(path)
            case "docx":
                return load_docx_document(path)
            case "txt" | "md" | "markdown":
                return load_text_document(path)
            case _:
                raise DocumentParsingError(f"No loader is configured for .{file_type} files")
    except (OSError, ValueError) as error:
        raise DocumentParsingError("Unable to extract text from the stored document") from error


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + (chunk_size // 2), end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def split_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Prefer paragraph boundaries, then split oversized text with a stable overlap."""
    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size")
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_text(paragraph, chunk_size, overlap))
        elif not current:
            current = paragraph
        elif len(current) + 2 + len(paragraph) <= chunk_size:
            current = f"{current}\n\n{paragraph}"
        else:
            chunks.append(current)
            tail = current[-overlap:].strip() if overlap else ""
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
    if current:
        chunks.append(current)
    return chunks


def prepare_document(file_path: str | Path, file_type: str) -> list[DocumentChunk]:
    """Extract and chunk a document while preserving source page information."""
    settings = get_settings()
    chunks: list[DocumentChunk] = []
    for page in extract_pages(file_path, file_type):
        text = clean_text(page.text)
        if not text:
            continue
        for content in split_text(
            text, chunk_size=settings.chunk_size_characters, overlap=settings.chunk_overlap_characters
        ):
            chunks.append(DocumentChunk(content=content, chunk_index=len(chunks), page_number=page.page_number))
    if not chunks:
        raise DocumentParsingError("The document does not contain extractable text")
    return chunks
