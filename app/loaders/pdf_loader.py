"""PDF text extraction loader."""

from pathlib import Path

from pypdf import PdfReader

from app.loaders.base import LoadedPage


def load_pdf_document(path: Path) -> list[LoadedPage]:
    """Extract text page-by-page so later citations can retain page references."""
    reader = PdfReader(str(path))
    return [LoadedPage(text=page.extract_text() or "", page_number=index) for index, page in enumerate(reader.pages, 1)]
