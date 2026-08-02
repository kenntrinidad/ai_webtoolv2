"""Configured AI agent persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.persona import utc_now

if TYPE_CHECKING:
    from app.models.document import KnowledgeDocument
    from app.models.persona import Persona


class Agent(Base):
    """An AI agent with identity, lifecycle state, and an optional reusable persona."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_id: Mapped[str | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    persona: Mapped["Persona | None"] = relationship(back_populates="agents")
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", passive_deletes=True
    )
