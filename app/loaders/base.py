"""Shared document-loader types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedPage:
    """Text extracted from a logical source page, when page information exists."""

    text: str
    page_number: int | None = None
