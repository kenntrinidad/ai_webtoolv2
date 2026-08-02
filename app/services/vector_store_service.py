"""Agent-isolated ChromaDB collection management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import chromadb
from chromadb.api import ClientAPI

from app.core.config import get_settings
from app.models import KnowledgeDocument
from app.services.ingestion_service import DocumentChunk


@dataclass(frozen=True)
class KnowledgeSearchResult:
    """A retrieved chunk with source metadata for later RAG prompting."""

    content: str
    document_id: str
    filename: str
    chunk_index: int
    page_number: int | None
    distance: float | None


class VectorStoreError(RuntimeError):
    """Raised when ChromaDB storage or retrieval fails."""


class AgentVectorStore:
    """Owns all ChromaDB access and prevents cross-agent knowledge retrieval."""

    def __init__(self, client: ClientAPI | None = None) -> None:
        self._client = client or chromadb.PersistentClient(path=str(get_settings().chroma_persist_directory))

    @staticmethod
    def collection_name(agent_id: str) -> str:
        """Return the deterministic collection name for one agent."""
        return f"agent_{agent_id}"

    def create_agent_collection(self, agent_id: str):
        """Create or return the private vector collection for an agent."""
        try:
            return self._client.get_or_create_collection(
                name=self.collection_name(agent_id), metadata={"hnsw:space": "cosine"}
            )
        except Exception as error:
            raise VectorStoreError("Unable to create the agent knowledge collection") from error

    def add_document_chunks(
        self,
        *,
        agent_id: str,
        document: KnowledgeDocument,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Upsert source chunks into only the selected agent's collection."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk and embedding counts must match")
        if not chunks:
            return
        collection = self.create_agent_collection(agent_id)
        now = datetime.now(timezone.utc).isoformat()
        ids = [f"{document.id}_{chunk.chunk_index}_{document.checksum[:12]}" for chunk in chunks]
        metadatas: list[dict[str, str | int | float | bool]] = []
        for chunk in chunks:
            metadata: dict[str, str | int | float | bool] = {
                "agent_id": agent_id,
                "document_id": document.id,
                "filename": document.original_filename,
                "chunk_index": chunk.chunk_index,
                "checksum": document.checksum,
                "ingested_at": now,
            }
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            metadatas.append(metadata)
        try:
            collection.upsert(
                ids=ids,
                documents=[chunk.content for chunk in chunks],
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as error:
            raise VectorStoreError("Unable to store document vectors") from error

    def delete_document_vectors(self, agent_id: str, document_id: str) -> None:
        """Delete vectors only from the owning agent's collection."""
        try:
            collection = self._client.get_collection(self.collection_name(agent_id))
            collection.delete(where={"document_id": document_id})
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise VectorStoreError("Unable to delete document vectors") from error

    def search_agent_knowledge(
        self, *, agent_id: str, query_embedding: list[float], limit: int = 5
    ) -> list[KnowledgeSearchResult]:
        """Retrieve matching chunks strictly from the requested agent's collection."""
        if limit < 1:
            raise ValueError("Search limit must be at least one")
        try:
            collection = self._client.get_collection(self.collection_name(agent_id))
            response = collection.query(
                query_embeddings=[query_embedding], n_results=limit, include=["documents", "metadatas", "distances"]
            )
        except Exception as error:
            if "does not exist" in str(error).lower():
                return []
            raise VectorStoreError("Unable to search agent knowledge") from error
        documents = response.get("documents", [[]])[0] or []
        metadatas = response.get("metadatas", [[]])[0] or []
        distances = response.get("distances", [[]])[0] or []
        results: list[KnowledgeSearchResult] = []
        for content, metadata, distance in zip(documents, metadatas, distances, strict=True):
            metadata = metadata or {}
            results.append(
                KnowledgeSearchResult(
                    content=content,
                    document_id=str(metadata["document_id"]),
                    filename=str(metadata["filename"]),
                    chunk_index=int(metadata["chunk_index"]),
                    page_number=int(metadata["page_number"]) if "page_number" in metadata else None,
                    distance=float(distance) if distance is not None else None,
                )
            )
        return results


def get_vector_store() -> AgentVectorStore:
    """Build the configured persistent vector-store service."""
    return AgentVectorStore()
