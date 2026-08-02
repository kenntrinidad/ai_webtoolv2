"""Safe agent-scoped document storage and metadata lifecycle management."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import KnowledgeDocument


class DocumentValidationError(ValueError):
    """Raised when an upload fails a configured safety check."""


class DuplicateDocumentError(ValueError):
    """Raised when an agent already owns identical document content."""


class DocumentStorageError(RuntimeError):
    """Raised when a file cannot be stored or removed safely."""


def _sanitize_filename(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise DocumentValidationError("A filename is required")
    basename = Path(filename).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._")
    suffix = Path(safe_name).suffix.lower()
    if not safe_name or not suffix:
        raise DocumentValidationError("A filename with a supported extension is required")
    return safe_name, suffix


def _validate_upload(filename: str | None, content: bytes) -> tuple[str, str]:
    settings = get_settings()
    safe_name, suffix = _sanitize_filename(filename)
    if suffix not in settings.allowed_document_extensions:
        allowed = ", ".join(settings.allowed_document_extensions)
        raise DocumentValidationError(f"Unsupported file type. Allowed types: {allowed}")
    if not content:
        raise DocumentValidationError("Uploaded document is empty")
    if len(content) > settings.max_upload_size_bytes:
        raise DocumentValidationError("Uploaded document exceeds the configured size limit")
    return safe_name, suffix


def list_agent_documents(db: Session, agent_id: str) -> list[KnowledgeDocument]:
    """Return one agent's documents without exposing another agent's records."""
    statement = select(KnowledgeDocument).where(KnowledgeDocument.agent_id == agent_id)
    return list(db.scalars(statement.order_by(KnowledgeDocument.uploaded_at.desc())))


def get_agent_document(db: Session, agent_id: str, document_id: str) -> KnowledgeDocument | None:
    """Find a document only if it belongs to the requested agent."""
    statement = select(KnowledgeDocument).where(
        KnowledgeDocument.id == document_id, KnowledgeDocument.agent_id == agent_id
    )
    return db.scalar(statement)


def store_document(
    db: Session, *, agent_id: str, filename: str | None, content: bytes
) -> KnowledgeDocument:
    """Validate, store, checksum, and persist one uploaded knowledge document."""
    safe_name, suffix = _validate_upload(filename, content)
    checksum = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(KnowledgeDocument.id).where(
            KnowledgeDocument.agent_id == agent_id, KnowledgeDocument.checksum == checksum
        )
    )
    if existing is not None:
        raise DuplicateDocumentError("This agent already has an identical document")

    storage_root = get_settings().document_storage_path.resolve()
    agent_directory = storage_root / agent_id
    agent_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4()}{suffix}"
    destination = agent_directory / stored_filename
    temporary_destination = destination.with_suffix(f"{suffix}.uploading")

    try:
        temporary_destination.write_bytes(content)
        temporary_destination.replace(destination)
        document = KnowledgeDocument(
            agent_id=agent_id,
            original_filename=safe_name,
            stored_filename=stored_filename,
            file_type=suffix.lstrip("."),
            file_path=str(destination),
            file_size=len(content),
            checksum=checksum,
            sync_status="pending",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except IntegrityError as error:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise DuplicateDocumentError("This agent already has an identical document") from error
    except OSError as error:
        temporary_destination.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise DocumentStorageError("Unable to safely store the uploaded document") from error


def delete_agent_document(db: Session, document: KnowledgeDocument) -> None:
    """Remove a stored file and its metadata without allowing path traversal."""
    storage_root = get_settings().document_storage_path.resolve()
    path = Path(document.file_path).resolve()
    if not path.is_relative_to(storage_root):
        raise DocumentStorageError("Document path is outside configured storage")
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        raise DocumentStorageError("Unable to remove stored document") from error
    db.delete(document)
    db.commit()
