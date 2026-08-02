import chromadb

from app.models import KnowledgeDocument
from app.services.ingestion_service import DocumentChunk
from app.services.vector_store_service import AgentVectorStore


def test_agent_vector_collections_are_isolated() -> None:
    store = AgentVectorStore(client=chromadb.Client())
    document_a = KnowledgeDocument(
        id="document-a",
        agent_id="agent-a",
        original_filename="a.txt",
        stored_filename="a.txt",
        file_type="txt",
        file_path="a.txt",
        file_size=1,
        checksum="checksum-a",
    )
    document_b = KnowledgeDocument(
        id="document-b",
        agent_id="agent-b",
        original_filename="b.txt",
        stored_filename="b.txt",
        file_type="txt",
        file_path="b.txt",
        file_size=1,
        checksum="checksum-b",
    )
    chunk_a = DocumentChunk(content="returns are allowed for thirty days", chunk_index=0, page_number=2)
    chunk_b = DocumentChunk(content="engineering deployment instructions", chunk_index=0, page_number=None)

    store.add_document_chunks(agent_id="agent-a", document=document_a, chunks=[chunk_a], embeddings=[[1.0, 0.0]])
    store.add_document_chunks(agent_id="agent-b", document=document_b, chunks=[chunk_b], embeddings=[[0.0, 1.0]])

    results = store.search_agent_knowledge(agent_id="agent-a", query_embedding=[1.0, 0.0])

    assert [result.document_id for result in results] == ["document-a"]
    assert results[0].filename == "a.txt"
    assert results[0].page_number == 2

    store.delete_document_vectors("agent-a", "document-a")
    assert store.search_agent_knowledge(agent_id="agent-a", query_embedding=[1.0, 0.0]) == []
