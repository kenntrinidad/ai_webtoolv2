"""Pydantic contracts for the agent chat API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """One user message sent to a configured agent."""

    message: str = Field(min_length=1, max_length=10_000)


class ChatSource(BaseModel):
    """Citation metadata returned with a RAG-backed response."""

    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int


class ChatResponse(BaseModel):
    """Agent answer plus the knowledge sources used to formulate it."""

    answer: str
    sources: list[ChatSource]
