"""Pydantic contracts for the agent chat API."""
from typing import Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: str | None = None
    sender_type: Literal["human", "api"] = "human"
    sender_origin: str = Field(default="playground", min_length=1, max_length=64)

class ChatSource(BaseModel):
    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int

class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    conversation_id: str