# Development Prompt: Configuration & Conversation Sidebar Features

## Context

AI Agent Builder is a FastAPI + SQLAlchemy application (MVP complete through Phase 15, User Management extension complete through Phase D) that lets an admin configure AI Agents, reusable Personas, agent-scoped Knowledge (RAG via per-agent Chroma collections), and chat with Agents through a session-authenticated admin UI. This prompt specifies two new top-level sidebar sections to be added to that admin UI: **Configuration** and **Conversation**.

Use the existing architecture boundaries (routes in `app/api/`, persistence in `app/models/`, contracts in `app/schemas/`, business logic in `app/services/`, UI in `app/static/` + `app/templates/`) and existing patterns (session auth required on all business routes, generic `500` on unexpected errors, `422` on validation errors without echoing submitted values).

---

## Feature 1: "Configuration" sidebar section

### Purpose
A single consolidated screen where an admin selects an Agent and, for that Agent, sets its Persona, its Knowledge Base attachment, and its LLM generation parameters (Temperature, max response tokens) — replacing the current arrangement where these settings live inside the Agent edit form.

### Functional requirements
1. **Agent selector** — dropdown/list of existing Agents (active and inactive, inactive visually distinguished). Selecting an Agent loads its current configuration into the panel below.
2. **Persona assignment** — dropdown of existing Personas (plus "None"). Saves to the Agent's `persona_id`, consistent with the existing `PUT /api/agents/{id}` contract (`"persona_id": null` clears the assignment).
3. **Knowledge Base attachment** — dropdown of the Agent's synchronized Knowledge Base(s)/documents (status = synced/ready only, or clearly marked if syncing/failed). Selecting attaches that knowledge source to the Agent for RAG retrieval.
4. **Temperature control** — a slider/scroll control ranging **0.0 to 2.0** (not the previously-planned 0.0–1.0 range), stepped appropriately (e.g. 0.1 increments), with the numeric value visible next to the slider. Persisted per-Agent and passed through to the LLM provider call on every chat request for that Agent.
5. **Max response tokens control** — numeric input or slider for the LLM `max_tokens` (or equivalent) parameter, persisted per-Agent and passed through to the LLM provider call.
6. **Save/apply** — explicit save action per Agent; show success/failure feedback. Failures follow existing error-handling conventions (safe `422`/`500`, no internal error detail exposed).

### Data model
- Add `temperature` (float, default e.g. 0.7, range-validated 0.0–2.0) and `max_tokens` (int, sensible default and bounds) columns to the `Agent` model (or a related `AgentConfiguration` table if the team prefers not to widen `Agent` directly — pick one and note the choice in the PR).
- No changes needed to `Persona` or `KnowledgeDocument` models; this feature only changes how they're **assigned/selected**, not what they store.

### API
- Extend `PUT /api/agents/{id}` (or add `PUT /api/agents/{id}/configuration`) to accept `temperature` and `max_tokens`, validated server-side against allowed ranges.
- Reuse existing `GET /api/personas`, `GET /api/agents/{agent_id}/documents`, and knowledge status endpoints to populate the dropdowns — no new read endpoints should be needed unless the Knowledge Base dropdown needs a "ready-only" filtered list, in which case add a query param (e.g. `?status=synced`) rather than a new route.

### LLM integration requirement
- Verify `OpenAICompatibleLLMProvider` actually forwards `temperature` and `max_tokens` on every call — this was previously reported as a bug (Temperature setting not affecting output, still hallucinating at 0.0). This must be fixed/verified as part of this feature, with a test asserting the provider call receives the configured values.

### UI
- New "Configuration" entry in the sidebar (see Feature 3 below for the sidebar bug that must not regress).
- Single-page layout: Agent selector at top, then Persona / Knowledge Base / Temperature / Max Tokens in one form below, matching the existing admin UI's visual style.

---

## Feature 2: "Conversation" sidebar section

### Purpose
A history view of past conversations with each Agent, showing who sent each message — a real human (via the admin Chat Testing Playground or an end-user channel) versus an API-originated message (e.g. Facebook Messenger webhook or direct API call).

### Functional requirements
1. **Conversation list** — list/table of conversations, filterable by Agent, with the most recent first. Each row shows Agent name, message count, last activity timestamp.
2. **Conversation detail view** — selecting a conversation shows the full message thread in order, each message tagged with:
   - **Sender type**: `human` (real end user / admin tester) vs `api` (system/webhook-originated), clearly labeled/badged in the UI.
   - Timestamp, and for Agent responses, which knowledge sources (if any) were cited.
3. **Sender attribution source** — this must reflect the actual origin of each message (e.g. Chat Testing Playground vs Facebook Messenger webhook vs any other integration channel), not be inferred/guessed.

### Data model
- A `conversations` table records recorded conversations — this was previously reported as broken ("no rows recorded in conversations table despite real conversations"); this must be fixed/verified as part of this feature.
- Each message row needs a `sender_type` (or equivalent) field distinguishing human vs API origin, populated at write time by whichever endpoint creates the message (Chat Testing Playground endpoint vs. any external-channel webhook endpoint).

### API
- `GET /api/conversations` — list conversations, filterable by `agent_id`.
- `GET /api/conversations/{id}/messages` — full message thread for one conversation, including `sender_type` per message.
- Ensure `POST /api/agents/{agent_id}/chat` (and any external-channel entry point) actually writes a conversation + message row on every call — this is the fix for the "no rows recorded" bug.

### UI
- New "Conversation" entry in the sidebar.
- List view + detail/thread view, matching existing admin UI style; sender-type badge on each message bubble.

---

## Feature 3: Sidebar menu bug fix (prerequisite / must not regress)

### Problem
Clicking a sidebar menu item currently causes the menu options to change or reorder, instead of only updating which item is marked active/selected.

### Requirement
Fix the sidebar so that:
- The set and order of menu items is stable and does not change on click.
- Only the active/selected state (highlight) updates based on the current route/view.
- The new "Configuration" and "Conversation" items must be added to this now-stable sidebar without triggering the same reordering bug.

---

## Acceptance criteria (all features)

- [ ] Sidebar shows stable, non-reordering menu including new "Configuration" and "Conversation" items.
- [ ] Configuration screen: selecting an Agent loads its Persona, Knowledge Base, Temperature (0.0–2.0), and Max Tokens; saving persists all four; LLM calls for that Agent actually use the saved Temperature and Max Tokens (verified by test).
- [ ] Conversation screen: lists conversations per Agent; detail view shows full thread with correct human-vs-API sender labeling; conversation/message rows are reliably written for every chat interaction (Playground and any external channel).
- [ ] All new/changed endpoints follow existing conventions: session-auth required, `422` for validation errors (no echoed submitted values), generic `500` for unexpected failures.
- [ ] Test coverage added for: temperature/max_tokens persistence and pass-through to the LLM provider; conversation/message row creation; sender_type correctness; sidebar active-state behavior (if UI tests exist in the suite).

## Out of scope for this prompt
- Renaming "Tenants" → "Systems" and related field renames (tracked separately).
- Extracting Knowledge Base into a fully standalone create/manage feature independent of Agent Configuration (tracked separately) — this prompt only covers *selecting* an existing Knowledge Base from Configuration, not creating/managing one there.
- Streaming/typing-effect chat responses and markdown rendering fixes (tracked separately).
