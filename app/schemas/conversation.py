"""Contracts for recorded agent conversations."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict
from app.schemas.chat import ChatSource

class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent_id: str
    agent_name: str
    message_count: int
    last_activity_at: datetime

class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sender_type: Literal["human", "api"]
    sender_origin: str
    role: str
    content: str
    sources: list[ChatSource]
    created_at: datetime