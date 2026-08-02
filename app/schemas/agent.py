"""Pydantic contracts for Agent API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AgentStatus = Literal["active", "inactive"]


class AgentCreate(BaseModel):
    """Payload required to create an agent."""

    name: str = Field(min_length=1, max_length=120)
    nickname: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    persona_id: str | None = None
    status: AgentStatus = "active"


class AgentUpdate(BaseModel):
    """Supplied fields update an agent; `persona_id: null` unassigns its persona."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    nickname: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    persona_id: str | None = None
    status: AgentStatus | None = None


class AgentRead(BaseModel):
    """Agent representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    nickname: str | None
    description: str | None
    persona_id: str | None
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
