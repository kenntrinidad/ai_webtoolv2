"""Per-agent external Messenger channel configuration."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.persona import utc_now

class AgentWebhookConfig(Base):
    __tablename__ = "agent_webhook_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    verify_token: Mapped[str] = mapped_column(String(255), nullable=False)
    page_access_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    page_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)