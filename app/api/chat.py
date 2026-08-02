"""REST endpoint for testing a configured agent with RAG-backed chat."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services import agent_service, chat_service
from app.services.embedding_service import EmbeddingProvider, EmbeddingProviderError, get_embedding_provider
from app.services.llm_service import LLMProvider, LLMProviderError, get_llm_provider
from app.services.vector_store_service import AgentVectorStore, VectorStoreError, get_vector_store

router = APIRouter(prefix="/agents/{agent_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_with_agent(
    agent_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: AgentVectorStore = Depends(get_vector_store),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """Generate one answer using the selected agent's identity and private knowledge."""
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    try:
        result = chat_service.generate_response(
            db,
            agent=agent,
            message=payload.message,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )
    except chat_service.AgentInactiveError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is inactive") from error
    except (EmbeddingProviderError, LLMProviderError, VectorStoreError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable")
    return ChatResponse(
        answer=result.answer,
        sources=[ChatSource(**source.__dict__) for source in result.sources],
    )
