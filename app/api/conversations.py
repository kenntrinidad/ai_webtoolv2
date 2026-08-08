"""Read endpoints for recorded agent conversations."""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.chat import ChatSource
from app.schemas.conversation import ConversationMessageRead, ConversationRead
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("", response_model=list[ConversationRead])
def list_conversations(agent_id: str | None = None, db: Session = Depends(get_db)):
    return conversation_service.list_conversations(db, agent_id=agent_id)

@router.get("/{conversation_id}/messages", response_model=list[ConversationMessageRead])
def list_messages(conversation_id: str, db: Session = Depends(get_db)):
    conversation = conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return [ConversationMessageRead(id=m.id, sender_type=m.sender_type, sender_origin=m.sender_origin, role=m.role, content=m.content, sources=[ChatSource(**source) for source in json.loads(m.sources or "[]")], created_at=m.created_at) for m in conversation.messages]