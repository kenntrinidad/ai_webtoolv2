from types import SimpleNamespace

from app.core.config import Settings
from app.services.llm_service import OpenAICompatibleLLMProvider, build_llm_input


class FakeCompletions:
    def __init__(self) -> None:
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="  Verified answer.  "))])


def test_openai_compatible_provider_keeps_message_boundaries() -> None:
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenAICompatibleLLMProvider(
        Settings(openai_api_key="test-key", llm_model="test-model"), client=client
    )

    answer = provider.generate_response(
        system_prompt="Trusted system instruction.",
        user_message="What is the return policy?",
        rag_context="[BEGIN UNTRUSTED KNOWLEDGE]\n30 days\n[END UNTRUSTED KNOWLEDGE]",
        max_tokens=256,
        temperature=0.3,
    )

    assert answer == "Verified answer."
    assert completions.request["model"] == "test-model"
    assert completions.request["max_tokens"] == 256
    assert completions.request["temperature"] == 0.3
    assert completions.request["messages"][0] == {"role": "system", "content": "Trusted system instruction."}
    assert "RETRIEVED KNOWLEDGE:" in completions.request["messages"][1]["content"]
    assert "USER MESSAGE:" in completions.request["messages"][1]["content"]


def test_llm_input_structures_rag_context_and_user_message() -> None:
    payload = build_llm_input(user_message="Hello", rag_context="No retrieved knowledge is available.")

    assert payload.endswith("USER MESSAGE:\nHello")
