"""REST endpoints for configured AI Agents."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Persona
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


def _require_agent(db: Session, agent_id: str):
    agent = agent_service.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _validate_persona_assignment(db: Session, persona_id: str | None) -> None:
    if persona_id is not None and db.get(Persona, persona_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    """Create an agent and optionally assign a reusable persona."""
    _validate_persona_assignment(db, payload.persona_id)
    try:
        return agent_service.create_agent(db, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent name already exists") from error


@router.get("", response_model=list[AgentRead])
def list_agents(db: Session = Depends(get_db)):
    """List configured agents."""
    return agent_service.list_agents(db)


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Return one configured agent."""
    return _require_agent(db, agent_id)


@router.put("/{agent_id}", response_model=AgentRead)
def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)):
    """Update identity, persona assignment, or active/inactive status."""
    agent = _require_agent(db, agent_id)
    if "persona_id" in payload.model_fields_set:
        _validate_persona_assignment(db, payload.persona_id)
    try:
        return agent_service.update_agent(db, agent, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent name already exists") from error


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Session = Depends(get_db)) -> Response:
    """Delete an agent."""
    agent_service.delete_agent(db, _require_agent(db, agent_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
