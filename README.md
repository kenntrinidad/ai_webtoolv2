
## To run python -m uvicorn ai_webtoolv2.app.main:app --host 127.0.0.1 --port 8000
##URL http://127.0.0.1:8000

# AI Agent Builder

Local MVP for configuring AI agents, reusable personas, agent-specific knowledge, and RAG-backed chat. The MVP is complete through **Phase 15**, including security hardening, documentation, and deployment preparation.

> User Management extension: **Phase D complete** - authenticated password changes and first-login password-change enforcement are now available.

## Architecture decisions

- **FastAPI + Pydantic Settings:** typed HTTP layer and environment-only configuration.
- **SQLAlchemy:** SQLite is used locally; `DATABASE_URL` can later point to PostgreSQL without changing model code.
- **Provider boundaries:** LLM, embeddings, document loaders, vector storage, and feature services live in separate modules so no API route owns AI or persistence logic.
- **Agent-scoped knowledge:** later vector collections will be isolated by agent ID; document metadata will carry document ID, checksum, source location, and chunk index.
- **Security baseline:** secrets remain in `.env`; uploaded file contents will be treated as untrusted data when ingestion and RAG are added.

## Folder layout

```text
app/
  api/         HTTP route modules
  core/        configuration, database setup, security, shared concerns
  loaders/     document-type parsers
  models/      SQLAlchemy persistence models
  schemas/     Pydantic API contracts
  services/    agent, persona, ingestion, vector, RAG, and LLM logic
  static/      CSS and JavaScript for the admin UI
  templates/   server-rendered HTML templates
  main.py      application factory and route registration
storage/
  documents/   runtime uploaded documents (not committed)
  chroma_db/   runtime Chroma persistence (not committed)
tests/         automated tests
```

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set values as needed. Do not commit `.env`.
4. Start the app: `python -m uvicorn app.main:app --reload`
5. Check [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

## Verify

Run `python -m pytest`.

## Phase 2 data model

- **Persona** stores a reusable name, description, and system prompt. Multiple agents can use one persona.
- **Agent** stores its name, nickname, description, lifecycle status, and an optional persona assignment.
- **KnowledgeDocument** stores agent-owned file metadata and its synchronization state. The `(agent_id, checksum)` constraint prevents duplicate copies of the same document for one agent.

The database tables are created automatically at application startup. For this local MVP, this uses SQLAlchemy `create_all`; database migrations will be introduced before production deployment.

## Persona API

- `POST /api/personas` - create a reusable persona
- `GET /api/personas` - list personas
- `GET /api/personas/{id}` - retrieve one persona
- `PUT /api/personas/{id}` - update a persona
- `DELETE /api/personas/{id}` - delete a persona

The interactive request forms are available at `http://127.0.0.1:8000/docs`. Persona names are unique. Deleting a persona safely removes its assignment from agents without deleting the agents themselves.

## Agent API

- `POST /api/agents` - create an agent, with an optional `persona_id`
- `GET /api/agents` - list agents
- `GET /api/agents/{id}` - retrieve one agent
- `PUT /api/agents/{id}` - update identity, Persona assignment, or `active`/`inactive` status
- `DELETE /api/agents/{id}` - delete an agent

An assigned Persona must exist. Supply `"persona_id": null` in an update request to remove an existing assignment.

## Knowledge document API

- `POST /api/agents/{agent_id}/documents` - multipart upload using the `file` form field
- `GET /api/agents/{agent_id}/documents` - list one agent's document metadata
- `DELETE /api/agents/{agent_id}/documents/{document_id}` - remove stored file and metadata

Uploads are limited by `MAX_UPLOAD_SIZE_BYTES` and `ALLOWED_DOCUMENT_EXTENSIONS` in `.env`. The MVP accepts PDF, TXT, Markdown, and DOCX. User filenames are sanitized, files are stored under an agent-specific directory with generated names, and a SHA-256 checksum prevents identical content from being uploaded twice to the same agent.

## Document parsing and chunking

The ingestion service extracts PDF page-by-page (retaining page numbers for future sources), and loads TXT, Markdown, and DOCX files through dedicated loader modules. It then normalizes whitespace and produces overlap-aware text chunks. Configure this behavior with `CHUNK_SIZE_CHARACTERS` and `CHUNK_OVERLAP_CHARACTERS`; overlap must be smaller than size. Chunks remain in memory at this phase and will be embedded into ChromaDB in Phase 7.

## Embeddings and vector store

`OpenAICompatibleEmbeddingProvider` isolates the OpenAI-compatible embedding API behind a small provider contract, so another provider can be added without changing RAG or route code. `AgentVectorStore` owns all ChromaDB access and creates one collection per agent (`agent_{agent_id}`), preventing cross-agent retrieval. Chunk metadata includes agent/document IDs, filename, checksum, chunk index, ingestion time, and PDF page number when available. `EMBEDDING_BATCH_SIZE` controls provider batch size. Phase 8 will connect document ingestion to these services through idempotent synchronization.

## Knowledge synchronization

- `POST /api/agents/{agent_id}/knowledge/sync` - process pending or changed documents
- `GET /api/agents/{agent_id}/knowledge/status` - view per-status document counts

Synchronization checks each stored file checksum. Unchanged synced documents are skipped; changed documents are marked outdated, their old vectors are deleted, and their text is extracted, embedded, and upserted again. Files that fail parsing, embedding, or vector storage are marked `failed` without exposing internal errors. Deleting a document also deletes its vectors first.

## RAG retrieval

`build_agent_system_prompt()` dynamically combines Agent identity, optional Persona instructions, and a knowledge policy. `retrieve_context()` embeds the user query, retrieves only from that agent's collection, and returns a context block plus citation-ready sources. Retrieved document text is visibly delimited as **untrusted knowledge**, so it cannot supersede the trusted system/persona instructions. The next phase will use these services to make a provider-neutral LLM request.

## LLM integration

`OpenAICompatibleLLMProvider` is isolated behind the `LLMProvider` contract. It sends the trusted system prompt in the system role and a separately structured payload containing retrieved knowledge and the user message. Set `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `LLM_MODEL`, and `EMBEDDING_MODEL` in `.env`. Supported provider values are `openai` and `mock`, where `mock` can be used for local development and testing without external API calls. No provider call occurs until the chat endpoint introduced in Phase 11 is used.

## Agent chat API

`POST /api/agents/{agent_id}/chat` accepts `{ "message": "..." }` and returns an `answer` plus the knowledge `sources` used. It builds the Agent's identity and Persona instructions, retrieves only that Agent's knowledge, and sends the result to the configured LLM provider. Deactivated Agents return `409`; unavailable embedding, vector, or LLM providers return a safe `503` response.

## Administration interface

Open `http://127.0.0.1:8000/` for the lightweight admin interface. It provides Dashboard, Agent, Persona, Knowledge, and Chat views, supports create/edit/delete operations, and can upload and synchronize Agent-specific documents.

## Agent Testing Playground

The Chat view lists active Agents, shows the selected Agent's Persona and synchronized-knowledge summary, and sends messages to the Agent chat API. Responses remain in the browser test transcript and display any source documents/pages returned by RAG.

## Reliability and error handling

All unexpected server failures are logged server-side and return a generic `500` JSON response rather than a debug stack trace. Request validation returns a safe `422` response with field paths and human-readable messages, without echoing submitted values. The test suite covers API CRUD, document validation/storage, sync idempotency, vector isolation/deletion, RAG construction, LLM boundaries, chat sources/inactive agents, and these error-handling paths.

## Production preparation

Review [SECURITY.md](SECURITY.md) before deployment. It documents current controls, known MVP boundaries, and the production checklist. A non-root [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml) are included for container deployment. SQLite remains appropriate for local MVP development; use PostgreSQL, managed persistence, authentication, authorization, migrations, backups, and rate limiting before public production use.

## User Management and Authentication

Set `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` before the first startup to create the initial Admin account. The password is bcrypt-hashed and never stored in plain text. Bootstrap runs only when no Admin account exists; incomplete bootstrap configuration is safely skipped so existing local development can still start.

Set a long random `SESSION_SECRET_KEY` in `.env` before using login. In development, a missing value produces a temporary secret and signs users out after every server restart; production refuses to start without it. Use `POST /api/auth/login` with an `identifier` (username or email) and password, then use `GET /api/auth/me` to inspect the signed-in account or `POST /api/auth/logout` to end the session. All existing Agent, Persona, Knowledge, Sync, and Chat endpoints now require that session. Repeated failed logins are temporarily rate-limited per client.

The browser interface at `http://127.0.0.1:8000/` now opens on a login screen. Sign in with the same administrator credentials, then use **Sign out** in the workspace header when finished.

Authenticated users can change their password through `POST /api/auth/change-password`, supplying the current password and a policy-compliant replacement. Accounts marked `must_change_password` may use only authentication routes until this succeeds; business APIs return `403` until then. Initial administrator accounts are now created with this flag enabled, enforcing a first-login password change.

The pre-existing root `main.py` is an earlier command-line prototype and is intentionally left untouched. The new application entry point is `app/main.py`.
"# ai_webtoolv2" 

## RAG persistence
Synchronized chunks and embeddings are mirrored in the relational knowledge_chunks table for auditing and administration. Chroma remains the active retrieval engine, so behavior and retrieval performance are unchanged while PostgreSQL deployments retain a queryable record. SQLite stores the mirror embedding as JSON text; PostgreSQL can later migrate this column to pgvector without changing the sync contract.
