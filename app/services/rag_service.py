"""RAG retrieval and structured context construction."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.embedding_service import EmbeddingProvider
from app.services.vector_store_service import AgentVectorStore, KnowledgeSearchResult


@dataclass(frozen=True)
class RagSource:
    """Citation-ready source information associated with retrieved knowledge."""

    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int


@dataclass(frozen=True)
class RetrievedContext:
    """Structured data passed to the later LLM/chat layer."""

    context: str
    sources: list[RagSource]


def _format_result(index: int, result: KnowledgeSearchResult) -> str:
    source = f"Source {index}: {result.filename}"
    if result.page_number is not None:
        source += f", page {result.page_number}"
    return f"[BEGIN UNTRUSTED KNOWLEDGE - {source}]\n{result.content}\n[END UNTRUSTED KNOWLEDGE]"


def retrieve_context(
    *,
    agent_id: str,
    query: str,
    embedding_provider: EmbeddingProvider,
    vector_store: AgentVectorStore,
    limit: int = 5,
) -> RetrievedContext:
    """Embed a query, retrieve agent-private chunks, and build a safe context block."""
    normalized_query = query.strip()
    if not normalized_query:
        return RetrievedContext(context="No retrieved knowledge is available.", sources=[])
    embeddings = embedding_provider.embed_texts([normalized_query])
    if len(embeddings) != 1:
        raise RuntimeError("Embedding provider returned an unexpected query vector count")
    results = vector_store.search_agent_knowledge(
        agent_id=agent_id, query_embedding=embeddings[0], limit=limit
    )
    if not results:
        return RetrievedContext(context="No retrieved knowledge is available.", sources=[])
    return RetrievedContext(
        context="\n\n".join(_format_result(index, result) for index, result in enumerate(results, 1)),
        sources=[
            RagSource(
                document_id=result.document_id,
                filename=result.filename,
                page_number=result.page_number,
                chunk_index=result.chunk_index,
            )
            for result in results
        ],
    )
