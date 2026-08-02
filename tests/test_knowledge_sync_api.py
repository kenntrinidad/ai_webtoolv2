from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import create_app
from app.models import KnowledgeDocument
from app.services import document_service
from app.services.embedding_service import get_embedding_provider
from app.services.vector_store_service import get_vector_store
from tests.auth_helpers import allow_authenticated_requests


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.added: list[tuple[str, str, int]] = []
        self.deleted: list[tuple[str, str]] = []

    def add_document_chunks(self, *, agent_id, document, chunks, embeddings) -> None:
        assert len(chunks) == len(embeddings)
        self.added.append((agent_id, document.id, len(chunks)))

    def delete_document_vectors(self, agent_id: str, document_id: str) -> None:
        self.deleted.append((agent_id, document_id))


def test_knowledge_sync_is_idempotent_and_rebuilds_changed_documents(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(
        document_service, "get_settings", lambda: Settings(document_storage_path=tmp_path)
    )
    vector_store = FakeVectorStore()
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
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        agent_id = client.post("/api/agents", json={"name": "Sync Agent"}).json()["id"]
        uploaded = client.post(
            f"/api/agents/{agent_id}/documents",
            files={"file": ("guide.txt", b"Original knowledge content.", "text/plain")},
        ).json()

        first_sync = client.post(f"/api/agents/{agent_id}/knowledge/sync")
        assert first_sync.json()["processed"] == 1
        assert first_sync.json()["statuses"] == {"synced": 1}
        assert len(vector_store.added) == 1

        second_sync = client.post(f"/api/agents/{agent_id}/knowledge/sync")
        assert second_sync.json()["skipped"] == 1
        assert len(vector_store.added) == 1

        with testing_session() as db:
            document = db.get(KnowledgeDocument, uploaded["id"])
            assert document is not None
            Path(document.file_path).write_text("Changed knowledge content.", encoding="utf-8")

        changed_sync = client.post(f"/api/agents/{agent_id}/knowledge/sync")
        assert changed_sync.json()["processed"] == 1
        assert len(vector_store.added) == 2
        assert (agent_id, uploaded["id"]) in vector_store.deleted

        current_status = client.get(f"/api/agents/{agent_id}/knowledge/status")
        assert current_status.json()["statuses"] == {"synced": 1}

    app.dependency_overrides.clear()
