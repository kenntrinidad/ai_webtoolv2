"""Persistence operations for recorded agent conversations."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models import Agent, Conversation, ConversationMessage
from app.models.persona import utc_now
from app.services.rag_service import RagSource

def list_conversations(db: Session, *, agent_id: str | None = None) -> list[Conversation]:
    statement = select(Conversation).options(selectinload(Conversation.agent), selectinload(Conversation.messages))
    if agent_id:
        statement = statement.where(Conversation.agent_id == agent_id)
    return list(db.scalars(statement.order_by(Conversation.last_activity_at.desc())))

def get_conversation(db: Session, conversation_id: str | None) -> Conversation | None:
    if not conversation_id:
        return None
    return db.scalar(select(Conversation).where(Conversation.id == conversation_id).options(selectinload(Conversation.agent), selectinload(Conversation.messages)))

def record_user_message(db: Session, *, agent: Agent, conversation_id: str | None, content: str, sender_type: str, sender_origin: str) -> Conversation:
    conversation = get_conversation(db, conversation_id)
    if conversation is not None and conversation.agent_id != agent.id:
        raise ValueError("Conversation does not belong to this agent")
    if conversation is None:
        conversation = Conversation(agent_id=agent.id)
        db.add(conversation)
        db.flush()
    db.add(ConversationMessage(conversation_id=conversation.id, sender_type=sender_type, sender_origin=sender_origin, role="user", content=content))
    conversation.last_activity_at = utc_now()
    db.commit()
    db.refresh(conversation)
    return conversation

def record_agent_message(db: Session, *, conversation: Conversation, content: str, sources: list[RagSource]) -> None:
    db.add(ConversationMessage(conversation_id=conversation.id, sender_type="api", sender_origin="agent", role="assistant", content=content, sources=json.dumps([source.__dict__ for source in sources])))
    conversation.last_activity_at = utc_now()
    db.commit()