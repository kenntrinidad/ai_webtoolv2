"""Business logic for reusable persona management."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Agent, Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate


def create_persona(db: Session, payload: PersonaCreate) -> Persona:
    """Persist a new reusable persona."""
    persona = Persona(**payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


def list_personas(db: Session) -> list[Persona]:
    """Return personas in deterministic display order."""
    return list(db.scalars(select(Persona).order_by(Persona.name)))


def get_persona(db: Session, persona_id: str) -> Persona | None:
    """Find a persona by identifier."""
    return db.get(Persona, persona_id)


def update_persona(db: Session, persona: Persona, payload: PersonaUpdate) -> Persona:
    """Apply supplied fields to an existing persona."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)
    db.commit()
    db.refresh(persona)
    return persona


def delete_persona(db: Session, persona: Persona) -> None:
    """Remove a persona while retaining agents that previously used it."""
    db.execute(update(Agent).where(Agent.persona_id == persona.id).values(persona_id=None))
    db.delete(persona)
    db.commit()
