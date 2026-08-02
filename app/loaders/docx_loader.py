"""DOCX text extraction loader."""

from pathlib import Path

from docx import Document

from app.loaders.base import LoadedPage


def load_docx_document(path: Path) -> list[LoadedPage]:
    """Extract paragraph text from a Word document as one logical source page."""
    document = Document(str(path))
    return [LoadedPage(text="\n\n".join(paragraph.text for paragraph in document.paragraphs))]
