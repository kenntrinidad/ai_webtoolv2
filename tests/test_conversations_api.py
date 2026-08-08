from collections.abc import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.main import create_app
from app.services.embedding_service import get_embedding_provider
from app.services.llm_service import get_llm_provider
from app.services.vector_store_service import get_vector_store
from tests.auth_helpers import allow_authenticated_requests

class Embeddings:
    def embed_texts(self, texts): return [[0.0] for _ in texts]
class Vectors:
    def search_agent_knowledge(self, **kwargs): return []
class LLM:
    def generate_response(self, **kwargs): return "Recorded answer"

def test_chat_records_origin_and_conversation_messages():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app(); allow_authenticated_requests(app)
    def db() -> Generator[Session, None, None]:
        value = session()
        try: yield value
        finally: value.close()
    app.dependency_overrides.update({get_db: db, get_embedding_provider: Embeddings, get_vector_store: Vectors, get_llm_provider: LLM})
    with TestClient(app) as client:
        agent_id = client.post('/api/agents', json={'name': 'History Agent'}).json()['id']
        chat = client.post(f'/api/agents/{agent_id}/chat', json={'message': 'Hello', 'sender_type': 'human', 'sender_origin': 'playground'})
        assert chat.status_code == 200
        conversation_id = chat.json()['conversation_id']
        conversations = client.get(f'/api/conversations?agent_id={agent_id}').json()
        messages = client.get(f'/api/conversations/{conversation_id}/messages').json()
    assert conversations[0]['message_count'] == 2
    assert [(message['sender_type'], message['sender_origin']) for message in messages] == [('human', 'playground'), ('api', 'agent')]