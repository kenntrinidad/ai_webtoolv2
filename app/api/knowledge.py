"""REST endpoints for agent-specific knowledge document storage."""
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.document import KnowledgeDocumentRead
from app.services import agent_service, document_service
from app.services.knowledge_chunk_service import delete_document_chunks
from app.services.vector_store_service import AgentVectorStore, get_vector_store
router = APIRouter(prefix="/agents/{agent_id}/documents", tags=["knowledge"])
def _require_agent(db: Session, agent_id: str) -> None:
    if agent_service.get_agent(db, agent_id) is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
async def _read_upload(file: UploadFile) -> bytes:
    content=await file.read(get_settings().max_upload_size_bytes+1); await file.close(); return content
@router.post("", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(agent_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _require_agent(db, agent_id)
    try: return document_service.store_document(db, agent_id=agent_id, filename=file.filename, content=await _read_upload(file))
    except document_service.DocumentValidationError as error: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except document_service.DuplicateDocumentError as error: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except document_service.DocumentStorageError as error: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document storage failed") from error
@router.get("", response_model=list[KnowledgeDocumentRead])
def list_documents(agent_id: str, db: Session = Depends(get_db)):
    _require_agent(db, agent_id); return document_service.list_agent_documents(db, agent_id)
@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(agent_id: str, document_id: str, db: Session = Depends(get_db), vector_store: AgentVectorStore = Depends(get_vector_store)) -> Response:
    _require_agent(db, agent_id); document=document_service.get_agent_document(db, agent_id, document_id)
    if document is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        vector_store.delete_document_vectors(agent_id, document.id); delete_document_chunks(db, document.id); document_service.delete_agent_document(db, document)
    except document_service.DocumentStorageError as error: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document deletion failed") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)