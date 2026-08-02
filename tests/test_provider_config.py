from app.core.config import Settings
from app.services.embedding_service import create_embedding_provider, MockEmbeddingProvider
from app.services.llm_service import create_llm_provider, MockLLMProvider


def test_mock_providers_are_selectable_via_settings() -> None:
    settings = Settings(
        openai_api_key="ignored",
        llm_provider="mock",
        embedding_provider="mock",
    )

    llm_provider = create_llm_provider(settings)
    embedding_provider = create_embedding_provider(settings)

    assert isinstance(llm_provider, MockLLMProvider)
    assert isinstance(embedding_provider, MockEmbeddingProvider)
    assert llm_provider.generate_response(
        system_prompt="Hello",
        user_message="Hi",
        rag_context="No knowledge",
    ).startswith("[MOCK RESPONSE]")
    assert embedding_provider.embed_texts(["test"]) == [[0.0, 0.0, 0.0]]
