"""Plain-text and Markdown document loader."""

from pathlib import Path

from app.loaders.base import LoadedPage


def load_text_document(path: Path) -> list[LoadedPage]:
    """Load UTF-8 text (including BOM-prefixed files) as one logical source page."""
    return [LoadedPage(text=path.read_text(encoding="utf-8-sig"))]
