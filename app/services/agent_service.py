"""Business logic for configured agent management."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


def create_agent(db: Session, payload: AgentCreate) -> Agent:
    """Persist a configured AI agent."""
    agent = Agent(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(db: Session) -> list[Agent]:
    """Return agents in deterministic display order."""
    return list(db.scalars(select(Agent).order_by(Agent.name)))


def get_agent(db: Session, agent_id: str) -> Agent | None:
    """Find one agent by identifier."""
    return db.get(Agent, agent_id)


def update_agent(db: Session, agent: Agent, payload: AgentUpdate) -> Agent:
    """Apply supplied configuration fields to an agent."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


def delete_agent(db: Session, agent: Agent) -> None:
    """Delete an agent and its future agent-owned dependent records."""
    db.delete(agent)
    db.commit()
