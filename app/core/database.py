"""SQLAlchemy engine, session dependency, and schema initialization."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class shared by every persistence model."""


def _create_engine() -> Engine:
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a transaction session for future API dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_agent_columns() -> None:
    """Add agent-level settings columns for existing SQLite databases."""
    inspector = inspect(engine)
    if "agents" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("agents")}
    with engine.begin() as connection:
        if "max_tokens" not in existing_columns:
            connection.execute(text("ALTER TABLE agents ADD COLUMN max_tokens INTEGER NOT NULL DEFAULT 512"))
        if "temperature" not in existing_columns:
            connection.execute(text("ALTER TABLE agents ADD COLUMN temperature FLOAT NOT NULL DEFAULT 0.7"))
        if "knowledge_document_id" not in existing_columns:
            connection.execute(text("ALTER TABLE agents ADD COLUMN knowledge_document_id VARCHAR(36)"))
        if "conversation_messages" in inspector.get_table_names():
            message_columns = {column["name"] for column in inspector.get_columns("conversation_messages")}
            if "sender_origin" not in message_columns:
                connection.execute(text("ALTER TABLE conversation_messages ADD COLUMN sender_origin VARCHAR(64) NOT NULL DEFAULT 'playground'"))


def init_database() -> None:
    """Create MVP tables; Alembic migrations will replace this in a deployment phase."""
    import app.models  # noqa: F401 - registers model metadata before creating tables.

    Base.metadata.create_all(bind=engine)
    _ensure_agent_columns()
