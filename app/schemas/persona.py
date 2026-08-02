"""Pydantic contracts for Persona API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonaCreate(BaseModel):
    """Payload required to create a reusable persona."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    system_prompt: str = Field(min_length=1, max_length=20_000)


class PersonaUpdate(BaseModel):
    """Fields that can be changed on an existing persona."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)
    system_prompt: str | None = Field(default=None, min_length=1, max_length=20_000)


class PersonaRead(BaseModel):
    """Persona representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    system_prompt: str
    created_at: datetime
    updated_at: datetime
