"""Idempotent document-to-vector synchronization orchestration."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import KnowledgeDocument
from app.services.embedding_service import EmbeddingProvider
from app.services.ingestion_service import prepare_document
from app.services.knowledge_chunk_service import delete_document_chunks, replace_document_chunks
from app.services.vector_store_service import AgentVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeSyncResult:
    """Outcome of synchronizing all documents for one agent."""

    agent_id: str
    processed: int
    skipped: int
    failed: int
    statuses: dict[str, int]


def _current_checksum(document: KnowledgeDocument) -> tuple[str, int]:
    content = Path(document.file_path).read_bytes()
    return hashlib.sha256(content).hexdigest(), len(content)


def _set_document_status(db: Session, document: KnowledgeDocument, status: str) -> None:
    document.sync_status = status
    db.commit()


def agent_knowledge_status(db: Session, agent_id: str) -> dict[str, int]:
    """Return counts by status for an agent's private knowledge base."""
    rows = db.execute(
        select(KnowledgeDocument.sync_status, func.count(KnowledgeDocument.id))
        .where(KnowledgeDocument.agent_id == agent_id)
        .group_by(KnowledgeDocument.sync_status)
    )
    return {str(sync_status): int(count) for sync_status, count in rows}


def synchronize_agent_knowledge(
    db: Session,
    *,
    agent_id: str,
    embedding_provider: EmbeddingProvider,
    vector_store: AgentVectorStore,
) -> KnowledgeSyncResult:
    """Synchronize changed or pending documents while avoiding duplicate vectors."""
    documents = list(
        db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.agent_id == agent_id)
            .order_by(KnowledgeDocument.uploaded_at)
        )
    )
    processed = skipped = failed = 0
    for document in documents:
        try:
            checksum, file_size = _current_checksum(document)
            changed = checksum != document.checksum
            if document.sync_status == "synced" and not changed:
                skipped += 1
                continue
            if changed:
                _set_document_status(db, document, "outdated")
                vector_store.delete_document_vectors(agent_id, document.id)
                delete_document_chunks(db, document.id)
                document.checksum = checksum
                document.file_size = file_size
                db.commit()

            _set_document_status(db, document, "processing")
            chunks = prepare_document(document.file_path, document.file_type)
            embeddings = embedding_provider.embed_texts([chunk.content for chunk in chunks])
            vector_store.delete_document_vectors(agent_id, document.id)
            vector_store.add_document_chunks(
                agent_id=agent_id, document=document, chunks=chunks, embeddings=embeddings
            )
            replace_document_chunks(db, agent_id=agent_id, document=document, chunks=chunks, embeddings=embeddings)
            document.sync_status = "synced"
            document.last_synced_at = datetime.now(timezone.utc)
            db.commit()
            processed += 1
        except Exception:
            db.rollback()
            document.sync_status = "failed"
            db.commit()
            logger.exception("Knowledge synchronization failed for document %s", document.id)
            failed += 1
    return KnowledgeSyncResult(
        agent_id=agent_id,
        processed=processed,
        skipped=skipped,
        failed=failed,
        statuses=agent_knowledge_status(db, agent_id),
    )
