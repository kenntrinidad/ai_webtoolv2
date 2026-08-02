"""Provider-neutral LLM generation service for the agent chat pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from openai import OpenAI

from app.core.config import Settings, get_settings


class LLMProvider(Protocol):
    """Contract implemented by any chat-capable LLM provider."""

    def generate_response(self, *, system_prompt: str, user_message: str, rag_context: str) -> str:
        """Generate a response from trusted instructions, retrieved data, and a user message."""


class LLMProviderError(RuntimeError):
    """Raised when the configured LLM provider cannot generate a usable response."""


def build_llm_input(*, user_message: str, rag_context: str) -> str:
    """Keep retrieved data and user input structurally distinct for the LLM request."""
    return f"""RETRIEVED KNOWLEDGE:
{rag_context}

USER MESSAGE:
{user_message}"""


class OpenAICompatibleLLMProvider:
    """Chat Completions adapter for OpenAI and compatible providers."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if not settings.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is required to generate chat responses")
        client_options: dict[str, str] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_options["base_url"] = settings.openai_base_url
        self._client = client or OpenAI(**client_options)
        self._model = settings.llm_model

    def generate_response(self, *, system_prompt: str, user_message: str, rag_context: str) -> str:
        """Request a completion while preserving system/user role separation."""
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": build_llm_input(user_message=user_message, rag_context=rag_context)},
                ],
            )
            answer = completion.choices[0].message.content
        except Exception as error:
            raise LLMProviderError("LLM provider request failed") from error
        if not answer or not answer.strip():
            raise LLMProviderError("LLM provider returned an empty response")
        return answer.strip()


class MockLLMProvider:
    """In-memory LLM provider for local development and tests."""

    def generate_response(self, *, system_prompt: str, user_message: str, rag_context: str) -> str:
        return f"[MOCK RESPONSE]\n{system_prompt}\n{rag_context}\nUSER MESSAGE:\n{user_message}"


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Return the configured LLM provider for the given settings."""
    if settings.llm_provider == "openai":
        return OpenAICompatibleLLMProvider(settings)
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    raise LLMProviderError(f"Unsupported LLM provider: {settings.llm_provider}")


def get_llm_provider() -> LLMProvider:
    """Build the configured LLM provider at the application boundary."""
    return create_llm_provider(get_settings())
