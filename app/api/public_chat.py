"""Token-authorized endpoint for chat widgets embedded on approved websites."""

from collections import defaultdict, deque
from secrets import compare_digest
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services import agent_service, chat_service, conversation_service
from app.services.embedding_service import EmbeddingProvider, EmbeddingProviderError, get_embedding_provider
from app.services.llm_service import LLMProvider, LLMProviderError, get_llm_provider
from app.services.vector_store_service import AgentVectorStore, VectorStoreError, get_vector_store


router = APIRouter(prefix="/public/agents/{agent_id}/chat", tags=["public chat"])
_request_times: dict[str, deque[float]] = defaultdict(deque)


def _enforce_widget_access(
    request: Request,
    agent_id: str,
    db: Session,
    settings: Settings,
):
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in settings.widget_allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Website origin is not allowed")

    agent = agent_service.get_agent(db, agent_id)
    token = request.headers.get("x-widget-token", "")
    if agent is None or not token or not compare_digest(token, agent.public_widget_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid widget token")
    if agent.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is inactive")

    client_ip = request.client.host if request.client else "unknown"
    key = f"{agent_id}:{client_ip}"
    now = monotonic()
    requests = _request_times[key]
    while requests and now - requests[0] >= 60:
        requests.popleft()
    if len(requests) >= settings.widget_requests_per_minute:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many chat requests")
    requests.append(now)
    return agent


@router.post("", response_model=ChatResponse)
def public_chat_with_agent(
    agent_id: str,
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: AgentVectorStore = Depends(get_vector_store),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    """Generate a chat reply for an approved, token-identified website widget."""
    agent = _enforce_widget_access(request, agent_id, db, settings)
    try:
        conversation = conversation_service.record_user_message(
            db,
            agent=agent,
            conversation_id=payload.conversation_id,
            content=payload.message,
            sender_type="api",
            sender_origin="website-widget",
        )
        result = chat_service.generate_response(
            db,
            agent=agent,
            message=payload.message,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid conversation") from error
    except (EmbeddingProviderError, LLMProviderError, VectorStoreError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service is unavailable") from error

    conversation_service.record_agent_message(db, conversation=conversation, content=result.answer, sources=result.sources)
    return ChatResponse(
        answer=result.answer,
        sources=[ChatSource(**source.__dict__) for source in result.sources],
        conversation_id=conversation.id,
    )
