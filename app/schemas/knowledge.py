"""Response contracts for knowledge synchronization."""

from pydantic import BaseModel


class KnowledgeSyncRead(BaseModel):
    """Summary of a synchronization run or current agent knowledge state."""

    agent_id: str
    processed: int
    skipped: int
    failed: int
    statuses: dict[str, int]
