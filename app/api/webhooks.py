"""Authenticated configuration and token-verified Messenger ingress."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import AgentWebhookConfig
from app.schemas.webhook import WebhookConfigRead, WebhookConfigUpdate
from app.services import agent_service, chat_service, conversation_service
from app.services.embedding_service import EmbeddingProvider, get_embedding_provider
from app.services.llm_service import LLMProvider, get_llm_provider
from app.services.vector_store_service import AgentVectorStore, get_vector_store

config_router = APIRouter(prefix="/agents/{agent_id}/webhook", tags=["webhooks"])
public_router = APIRouter(prefix="/webhooks/{agent_id}/messenger", tags=["webhooks"])
def mask(value: str | None) -> str | None:
    return None if not value else "•" * max(0, len(value)-4) + value[-4:]
def read_config(request: Request, agent_id: str, config: AgentWebhookConfig | None) -> WebhookConfigRead:
    return WebhookConfigRead(callback_url=str(request.base_url).rstrip("/") + f"/api/webhooks/{agent_id}/messenger", configured=config is not None, verify_token_masked=mask(config.verify_token) if config else None, page_access_token_masked=mask(config.page_access_token) if config else None, page_id=config.page_id if config else None)
@config_router.get("", response_model=WebhookConfigRead)
def get_config(agent_id: str, request: Request, db: Session = Depends(get_db)):
    if agent_service.get_agent(db, agent_id) is None: raise HTTPException(404, "Agent not found")
    return read_config(request, agent_id, db.query(AgentWebhookConfig).filter_by(agent_id=agent_id).one_or_none())
@config_router.put("", response_model=WebhookConfigRead)
def put_config(agent_id: str, payload: WebhookConfigUpdate, request: Request, db: Session = Depends(get_db)):
    if agent_service.get_agent(db, agent_id) is None: raise HTTPException(404, "Agent not found")
    config = db.query(AgentWebhookConfig).filter_by(agent_id=agent_id).one_or_none()
    if config is None:
        if not payload.verify_token: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Verify token is required")
        config=AgentWebhookConfig(agent_id=agent_id, verify_token=payload.verify_token); db.add(config)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None: setattr(config, key, value)
    db.commit(); db.refresh(config)
    return read_config(request, agent_id, config)
@public_router.get("")
def verify(agent_id: str, hub_mode: str = Query(alias="hub.mode"), hub_verify_token: str = Query(alias="hub.verify_token"), hub_challenge: str = Query(alias="hub.challenge"), db: Session = Depends(get_db)):
    config=db.query(AgentWebhookConfig).filter_by(agent_id=agent_id).one_or_none()
    if not config or hub_mode != "subscribe" or hub_verify_token != config.verify_token: raise HTTPException(403, "Webhook verification failed")
    return Response(content=hub_challenge, media_type="text/plain")
@public_router.post("")
async def receive(agent_id: str, request: Request, db: Session = Depends(get_db), embedding_provider: EmbeddingProvider = Depends(get_embedding_provider), vector_store: AgentVectorStore = Depends(get_vector_store), llm_provider: LLMProvider = Depends(get_llm_provider)):
    config=db.query(AgentWebhookConfig).filter_by(agent_id=agent_id).one_or_none()
    if not config: raise HTTPException(404, "Webhook is not configured")
    body=await request.json(); entries=body.get("entry", [])
    messages=[event.get("message", {}) for entry in entries for event in entry.get("messaging", [])]
    replies=[]; agent=agent_service.get_agent(db, agent_id)
    for message in messages:
        text=message.get("text")
        if not text: continue
        conversation=conversation_service.record_user_message(db, agent=agent, conversation_id=None, content=text, sender_type="api", sender_origin="messenger")
        result=chat_service.generate_response(db, agent=agent, message=text, embedding_provider=embedding_provider, vector_store=vector_store, llm_provider=llm_provider)
        conversation_service.record_agent_message(db, conversation=conversation, content=result.answer, sources=result.sources)
        replies.append({"recipient_id": message.get("sender", {}).get("id"), "message": result.answer})
    return {"received": len(replies), "replies": replies}