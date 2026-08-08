# Development Prompt: Conversation Fix, RAG Persistence, Chat API & Webhook Setup

## Context

Builds on `DEV_PROMPT_configuration_conversation.md` (Configuration and Conversation sidebar sections). This prompt covers: fixing Conversation history not displaying, adding dedicated PostgreSQL tables (database `ai_webtool_db`) for conversations and for RAG/chunk/embedding data, and adding a "chat API + webhook setup" view inside Configuration.

---

## Bug: Conversation section not displaying chat history

### Symptom
The Conversation sidebar section shows no chat history even after real conversations have happened via the Agent chat API / Testing Playground.

### Likely root causes to investigate (in order)
1. **Write path** — confirm `POST /api/agents/{agent_id}/chat` actually inserts a conversation row (and message rows) on every call. This was previously flagged ("no rows recorded in conversations table despite real conversations") and may not have been fully fixed.
2. **Read path** — confirm `GET /api/conversations` and `GET /api/conversations/{id}/messages` query the correct table/columns and aren't filtering on a field (e.g. `agent_id`, `sender_type`, a status flag) that's null or mismatched on existing rows.
3. **Frontend** — confirm the Conversation view is actually calling the list/detail endpoints and rendering the response, rather than pointing at a stale/mock endpoint.

### Fix requirement
- Trace and fix the actual break point (don't assume; verify with a manual chat call + DB check).
- Add a regression test: send a chat message, then assert a conversation + message row exists and is returned by the list/detail endpoints.

---

## Feature: Conversations table (PostgreSQL, `ai_webtool_db`)

### Purpose
Persist conversation and message history per Agent in the relational database, replacing any in-memory or missing persistence.

### Schema (proposed)
**`conversations`**
| column | type | notes |
|---|---|---|
| id | UUID/PK | |
| agent_id | FK → agents.id | required |
| started_at | timestamptz | |
| last_message_at | timestamptz | updated on each new message |
| channel | text | e.g. `playground`, `messenger`, `api` — origin of the conversation |

**`conversation_messages`**
| column | type | notes |
|---|---|---|
| id | UUID/PK | |
| conversation_id | FK → conversations.id | required |
| sender_type | text | `human` or `api` (see prior Conversation spec) |
| role | text | `user` or `assistant` |
| content | text | message body |
| sources | JSONB | RAG source citations returned with this message, if any |
| created_at | timestamptz | |

### API
- `POST /api/agents/{agent_id}/chat` writes to these tables on every call (fixes the bug above).
- `GET /api/conversations?agent_id=` — list.
- `GET /api/conversations/{id}/messages` — thread detail.

---

## Feature: RAG chunk/embedding table (PostgreSQL, `ai_webtool_db`)

### Purpose
Store chunked and embedded knowledge in the relational database itself (mapped to the owning Agent and source document), rather than relying solely on the existing Chroma vector store. This gives the admin UI a queryable, relational record of exactly what knowledge exists, how it was chunked, and which Agent it's mapped to — useful for the Knowledge Base browsing/management UI and for debugging retrieval, independent of Chroma internals.

### Schema (proposed)
**`knowledge_chunks`**
| column | type | notes |
|---|---|---|
| id | UUID/PK | |
| agent_id | FK → agents.id | required — enforces the existing per-agent isolation |
| document_id | FK → knowledge_documents.id | required |
| chunk_index | integer | position within the document |
| content | text | the chunk's raw text |
| embedding | vector | requires the `pgvector` extension on `ai_webtool_db`; store the same embedding produced for Chroma so both stay in sync, or migrate retrieval to query this table directly — pick one approach and document it in the PR |
| page_number | integer, nullable | carried over from PDF extraction when available |
| checksum | text | source document checksum, for sync/staleness checks |
| created_at | timestamptz | |

### Behavior requirements
- Populated by the existing knowledge synchronization flow (`POST /api/agents/{agent_id}/knowledge/sync`) — extend that service to write rows here in addition to (or instead of) upserting into Chroma. Decide and document whether Chroma remains the retrieval engine (this table becomes a mirror/audit log) or whether retrieval moves to `pgvector` similarity search against this table (this table becomes the source of truth). Either is acceptable; the choice must be explicit and consistent with `retrieve_context()`.
- Deleting a document deletes its `knowledge_chunks` rows (mirrors existing Chroma-deletion behavior).
- Changed documents mark old chunks outdated/deleted and re-chunk/re-embed, consistent with existing sync semantics.

---

## Feature: Chat API + Webhook setup in Configuration

### Purpose
From the Configuration screen (per-Agent), let the admin see how to call that Agent's chat API and configure an inbound webhook (e.g. for Facebook Messenger) without leaving the Configuration view.

### Functional requirements
1. **Chat API display** — show the Agent's chat endpoint (`POST /api/agents/{agent_id}/chat`), required auth/session note, and an example request/response payload for that specific Agent (with its real `agent_id` filled in).
2. **Webhook setup** — a form to configure the inbound webhook for this Agent: Webhook Callback URL (generated/displayed, pointing at this app), Verify Token, and channel-specific credentials (e.g. Facebook Page Access Token, Facebook Page ID) needed to connect an external channel to this Agent.
   - Reuse whatever webhook-handling route already exists for external channels; if none exists yet, this feature includes adding the receiving endpoint (e.g. `POST /api/webhooks/{agent_id}/messenger` and the `GET` verification handshake route).
   - Sensitive fields (tokens/keys) must be masked in the UI after saving, consistent with the existing security baseline (secrets not exposed once stored).
3. Messages arriving through the webhook must be written to `conversations`/`conversation_messages` with `sender_type = api` and `channel` set appropriately, so they show up correctly in the Conversation section.

---

## Acceptance criteria

- [ ] Conversation section reliably displays chat history for both Playground and API/webhook-originated conversations; root cause of the current failure is identified and fixed, with a regression test.
- [ ] `conversations` and `conversation_messages` tables exist in `ai_webtool_db` and are populated on every chat interaction, from every channel.
- [ ] `knowledge_chunks` table exists in `ai_webtool_db`, is populated by knowledge sync, stays consistent with document delete/update/re-sync behavior, and its relationship to Chroma retrieval is explicitly documented.
- [ ] Configuration screen shows the Agent's chat API details and a working webhook setup form; secrets are masked after save; webhook-received messages are correctly attributed as `api` in Conversation history.
- [ ] All new/changed endpoints follow existing conventions: session-auth required (webhook endpoints use their own verify-token auth instead, not session auth), `422` for validation errors, generic `500` for unexpected failures.

## Out of scope for this prompt
- Renaming "Tenants" → "Systems" and related field renames (tracked separately).
- Streaming/typing-effect chat responses and markdown rendering fixes (tracked separately).
- Non-Messenger channels (WhatsApp, SMS, etc.) — this prompt only requires the webhook plumbing to support at least one channel end-to-end; the pattern should generalize but additional channels are separate work.
