"""Pydantic response contract for agent knowledge documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentRead(BaseModel):
    """Safe document metadata exposed through the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    original_filename: str
    file_type: str
    file_size: int
    checksum: str
    sync_status: str
    uploaded_at: datetime
    last_synced_at: datetime | None
