"""Persist the relational RAG audit mirror alongside Chroma vectors."""
import json
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.models import KnowledgeChunk, KnowledgeDocument
from app.services.ingestion_service import DocumentChunk

def replace_document_chunks(db: Session, *, agent_id: str, document: KnowledgeDocument, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunk and embedding counts must match")
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    db.add_all([KnowledgeChunk(agent_id=agent_id, document_id=document.id, chunk_index=chunk.chunk_index, content=chunk.content, embedding=json.dumps(embedding), page_number=chunk.page_number, checksum=document.checksum) for chunk, embedding in zip(chunks, embeddings, strict=True)])

def delete_document_chunks(db: Session, document_id: str) -> None:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))