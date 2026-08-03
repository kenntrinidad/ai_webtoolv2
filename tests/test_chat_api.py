from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from app.services.embedding_service import get_embedding_provider
from app.services.llm_service import get_llm_provider
from app.services.vector_store_service import KnowledgeSearchResult, get_vector_store
from tests.auth_helpers import allow_authenticated_requests


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.2, 0.8] for _ in texts]


class FakeVectorStore:
    def search_agent_knowledge(self, *, agent_id: str, query_embedding: list[float], limit: int):
        return [
            KnowledgeSearchResult(
                content="Returns are accepted within 30 days.",
                document_id="document-1",
                filename="returns.pdf",
                chunk_index=1,
                page_number=2,
                distance=0.05,
            )
        ]


class FakeLLMProvider:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.rag_context = ""
        self.temperature = None

    def generate_response(
        self,
        *,
        system_prompt: str,
        user_message: str,
        rag_context: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        self.system_prompt = system_prompt
        self.rag_context = rag_context
        self.temperature = temperature
        return "Returns are accepted within 30 days."


def test_chat_endpoint_combines_agent_identity_rag_and_sources() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    llm_provider = FakeLLMProvider()
    app = create_app()
    allow_authenticated_requests(app)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_provider] = FakeEmbeddingProvider
    app.dependency_overrides[get_vector_store] = FakeVectorStore
    app.dependency_overrides[get_llm_provider] = lambda: llm_provider
    with TestClient(app) as client:
        persona_id = client.post(
            "/api/personas", json={"name": "Support", "system_prompt": "Be concise."}
        ).json()["id"]
        agent_id = client.post(
            "/api/agents",
            json={"name": "Customer Agent", "nickname": "JARVIS", "persona_id": persona_id, "temperature": 0.0},
        ).json()["id"]

        response = client.post(f"/api/agents/{agent_id}/chat", json={"message": "What is the return policy?"})
        client.put(f"/api/agents/{agent_id}", json={"status": "inactive"})
        inactive_response = client.post(f"/api/agents/{agent_id}/chat", json={"message": "Can you help?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "Returns are accepted within 30 days."
    assert response.json()["sources"] == [
        {"document_id": "document-1", "filename": "returns.pdf", "page_number": 2, "chunk_index": 1}
    ]
    assert llm_provider.temperature == 0.0
    assert "You are JARVIS." in llm_provider.system_prompt
    assert "Always answer only from the retrieved knowledge." in llm_provider.system_prompt
    assert "BEGIN UNTRUSTED KNOWLEDGE" in llm_provider.rag_context
    assert inactive_response.status_code == 409
    assert inactive_response.json()["detail"] == "Agent is inactive"
    app.dependency_overrides.clear()
