"""Agent chat orchestration across identity, RAG, and LLM provider services."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Agent
from app.services.embedding_service import EmbeddingProvider
from app.services.llm_service import LLMProvider
from app.services.prompt_service import build_agent_system_prompt
from app.services.rag_service import RagSource, retrieve_context
from app.services.vector_store_service import AgentVectorStore


class AgentInactiveError(RuntimeError):
    """Raised when a chat request targets a deactivated agent."""


@dataclass(frozen=True)
class ChatResult:
    """Generated response and the retrieval citations available to the UI."""

    answer: str
    sources: list[RagSource]


def generate_response(
    db: Session,
    *,
    agent: Agent,
    message: str,
    embedding_provider: EmbeddingProvider,
    vector_store: AgentVectorStore,
    llm_provider: LLMProvider,
) -> ChatResult:
    """Build trusted instructions, retrieve scoped knowledge, and generate an answer."""
    if agent.status != "active":
        raise AgentInactiveError("The selected agent is inactive")
    system_prompt = build_agent_system_prompt(agent)
    retrieved = retrieve_context(
        agent_id=agent.id,
        query=message,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )
    answer = llm_provider.generate_response(
        system_prompt=system_prompt,
        user_message=message,
        rag_context=retrieved.context,
        max_tokens=agent.max_tokens,
        temperature=agent.temperature,
    )
    return ChatResult(answer=answer, sources=retrieved.sources)
