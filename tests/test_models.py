from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Agent, KnowledgeDocument, Persona


def test_agent_persona_and_document_relationships_persist() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        persona = Persona(name="Professional Support", system_prompt="Be clear and polite.")
        agent = Agent(name="Customer Support", nickname="JARVIS", persona=persona)
        document = KnowledgeDocument(
            agent=agent,
            original_filename="faq.pdf",
            stored_filename="agent-faq.pdf",
            file_type="pdf",
            file_path="storage/documents/agent-faq.pdf",
            file_size=42,
            checksum="sha256:example",
        )
        session.add(document)
        session.commit()

        stored_agent = session.get(Agent, agent.id)
        assert stored_agent is not None
        assert stored_agent.persona is not None
        assert stored_agent.persona.name == "Professional Support"
        assert len(stored_agent.documents) == 1
        assert stored_agent.documents[0].sync_status == "pending"
