"""REST endpoints for reusable Persona configurations."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.persona import PersonaCreate, PersonaRead, PersonaUpdate
from app.services import persona_service

router = APIRouter(prefix="/personas", tags=["personas"])


def _require_persona(db: Session, persona_id: str):
    persona = persona_service.get_persona(db, persona_id)
    if persona is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return persona


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(payload: PersonaCreate, db: Session = Depends(get_db)):
    """Create a reusable system-prompt configuration."""
    try:
        return persona_service.create_persona(db, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Persona name already exists") from error


@router.get("", response_model=list[PersonaRead])
def list_personas(db: Session = Depends(get_db)):
    """List reusable persona configurations."""
    return persona_service.list_personas(db)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: str, db: Session = Depends(get_db)):
    """Return one persona configuration."""
    return _require_persona(db, persona_id)


@router.put("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: str, payload: PersonaUpdate, db: Session = Depends(get_db)):
    """Update a persona configuration."""
    persona = _require_persona(db, persona_id)
    try:
        return persona_service.update_persona(db, persona, payload)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Persona name already exists") from error


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: str, db: Session = Depends(get_db)) -> Response:
    """Delete a persona and clear it from any assigned agents."""
    persona_service.delete_persona(db, _require_persona(db, persona_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
