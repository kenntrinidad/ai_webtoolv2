"""Typed, environment-driven application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Agent Builder"
    app_env: str = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite:///./storage/ai_agent_builder.db"
    document_storage_path: Path = Path("storage/documents")
    chroma_persist_directory: Path = Path("storage/chroma_db")
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    allowed_document_extensions: tuple[str, ...] = (".pdf", ".txt", ".md", ".markdown", ".docx")
    chunk_size_characters: int = Field(default=1_000, ge=100, le=10_000)
    chunk_overlap_characters: int = Field(default=150, ge=0, le=2_000)
    embedding_batch_size: int = Field(default=100, ge=1, le=2_048)
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    llm_provider: str = "openai"
    embedding_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    initial_admin_username: str | None = None
    initial_admin_email: str | None = None
    initial_admin_password: SecretStr | None = None
    password_hash_rounds: int = Field(default=12, ge=10, le=15)
    session_secret_key: SecretStr | None = None
    session_cookie_name: str = "ai_agent_builder_session"
    login_max_attempts: int = Field(default=5, ge=1, le=20)
    login_attempt_window_seconds: int = Field(default=900, ge=60, le=86_400)
    login_lockout_seconds: int = Field(default=900, ge=60, le=86_400)

    @field_validator("allowed_document_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, value: str | tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip().lower() for item in value.split(",") if item.strip())
        return tuple(item.lower() for item in value)

    @field_validator("llm_provider", "embedding_provider", mode="before")
    @classmethod
    def parse_provider_names(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        if self.chunk_overlap_characters >= self.chunk_size_characters:
            raise ValueError("CHUNK_OVERLAP_CHARACTERS must be smaller than CHUNK_SIZE_CHARACTERS")
        if self.llm_provider not in {"openai", "mock"}:
            raise ValueError('LLM_PROVIDER must be one of: openai, mock')
        if self.embedding_provider not in {"openai", "mock"}:
            raise ValueError('EMBEDDING_PROVIDER must be one of: openai, mock')
        return self

    def ensure_storage_directories(self) -> None:
        """Create local runtime directories without creating database/vector data yet."""
        self.document_storage_path.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return the cached process-wide settings instance."""
    return Settings()
