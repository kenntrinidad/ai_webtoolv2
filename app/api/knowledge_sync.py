"""REST endpoints for explicit agent knowledge synchronization."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.knowledge import KnowledgeSyncRead
from app.services import agent_service, knowledge_sync_service
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider
from app.services.vector_store_service import AgentVectorStore, get_vector_store

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["knowledge"])


def _require_agent(db: Session, agent_id: str) -> None:
    if agent_service.get_agent(db, agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")


@router.post("/sync", response_model=KnowledgeSyncRead)
def sync_knowledge(
    agent_id: str,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: AgentVectorStore = Depends(get_vector_store),
):
    """Explicitly synchronize changed and pending documents for one agent."""
    _require_agent(db, agent_id)
    return knowledge_sync_service.synchronize_agent_knowledge(
        db, agent_id=agent_id, embedding_provider=embedding_provider, vector_store=vector_store
    )


@router.get("/status", response_model=KnowledgeSyncRead)
def knowledge_status(agent_id: str, db: Session = Depends(get_db)):
    """Report synchronization state counts without starting a new run."""
    _require_agent(db, agent_id)
    return KnowledgeSyncRead(
        agent_id=agent_id,
        processed=0,
        skipped=0,
        failed=0,
        statuses=knowledge_sync_service.agent_knowledge_status(db, agent_id),
    )
