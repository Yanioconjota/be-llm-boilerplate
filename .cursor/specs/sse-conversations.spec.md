# SSE Migration & Conversation Architecture Specification

## Overview

**Problem Statement:** The current backend uses WebSocket for streaming LLM responses but lacks conversation threading support. The system needs to be migrated to Server-Sent Events (SSE) for simpler client integration and extended to support full conversation history with context passing.

**Target Users:** Frontend developers building chat interfaces for LLM interactions (Angular/React)

**Success Criteria:**
- SSE endpoint streams LLM responses token-by-token
- Conversations are tracked with unique IDs
- Full conversation history is retrievable
- LLM receives conversation context for coherent multi-turn dialogues

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WebSocket | **Remove** | SSE is sufficient, simpler |
| Max messages | **100** | Plenty for demo, avoids complexity |
| Token counting | **Skip** | Adds complexity, not needed |
| Delete strategy | **Hard delete** | Simpler implementation |

---

## Functional Requirements

### FR-1: SSE Streaming Endpoint
**Description:** Server-Sent Events for LLM response streaming.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] `POST /conversations/{id}/stream` returns `text/event-stream` content type
- [ ] Streams tokens as SSE events: `data: {"chunk": "token", "done": false}`
- [ ] Supports cache hit scenario (simulated streaming)
- [ ] Handles Ollama errors gracefully with error events
- [ ] Connection closes automatically when `done: true`

### FR-2: Conversation Creation
**Description:** Users can create new conversation sessions.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] `POST /conversations` creates a new conversation
- [ ] Returns `{ id, created_at, title, model }`
- [ ] Conversation ID is a UUID

### FR-3: Message Streaming within Conversation
**Description:** Send prompts within a conversation context and stream responses.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] `POST /conversations/{id}/stream` accepts `{ prompt: string }`
- [ ] Stores user message before streaming
- [ ] Stores assistant message after streaming completes
- [ ] Returns 404 if conversation ID doesn't exist
- [ ] Passes conversation history to Ollama for context

### FR-4: Conversation Retrieval
**Description:** Retrieve full conversation history.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] `GET /conversations/{id}` returns conversation with all messages
- [ ] Messages ordered by timestamp (ascending)
- [ ] Each message includes role, content, timestamp
- [ ] Returns 404 if conversation doesn't exist

### FR-5: Conversation Listing
**Description:** List all conversations.
**Priority:** Should Have
**Acceptance Criteria:**
- [ ] `GET /conversations` returns paginated list
- [ ] Supports `?limit=20&offset=0` query params
- [ ] Returns summary (id, title, created_at, message_count, updated_at)
- [ ] Sorted by last activity (most recent first)

### FR-6: Context Passing to LLM
**Description:** Send conversation history to Ollama for contextual responses.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] Build prompt with conversation history (last 10 messages)
- [ ] Format: Alternating user/assistant messages + new prompt

### FR-7: Conversation Limit
**Description:** Limit conversations to 100 messages.
**Priority:** Must Have
**Acceptance Criteria:**
- [ ] Return error when conversation reaches 100 messages
- [ ] Error message suggests starting a new conversation

---

## Entities

### Conversation

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| id | string (UUID) | Yes | Unique conversation identifier |
| title | string | No | User-defined or auto-generated title |
| created_at | datetime | Yes | Conversation creation timestamp |
| updated_at | datetime | Yes | Last activity timestamp |
| model | string | Yes | LLM model used (default: llama3) |

### Message

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| id | string (UUID) | Yes | Unique message identifier |
| conversation_id | string | Yes | Parent conversation ID |
| role | enum | Yes | "user" \| "assistant" |
| content | string | Yes | Message text content |
| timestamp | datetime | Yes | When message was created |
| cached | boolean | No | Whether response was from cache (assistant only) |

---

## API Specification

### FastAPI Endpoints (Port 8000)

#### Conversations API

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/conversations` | Create new conversation | `{ title?, model? }` | `{ id, created_at, title, model }` |
| GET | `/conversations` | List conversations | Query: `limit`, `offset` | `{ items: [...], total, limit, offset }` |
| GET | `/conversations/{id}` | Get conversation with messages | - | `{ id, title, ..., messages: [...] }` |
| POST | `/conversations/{id}/stream` | Send message, stream response (SSE) | `{ prompt }` | `text/event-stream` |
| DELETE | `/conversations/{id}` | Delete conversation | - | `{ success: true }` |

#### SSE Event Format

```
event: message
data: {"chunk": "Hello", "done": false, "cached": false}

event: message  
data: {"chunk": " world", "done": false, "cached": false}

event: message
data: {"chunk": "", "done": true, "cached": false}

event: error
data: {"error": "llm_unavailable", "message": "Cannot connect to Ollama"}
```

#### Legacy Endpoints (Kept)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/joker` | Demo joke endpoint |
| POST | `/ask` | Stateless prompt (no conversation) |

### Storage Service Endpoints (Port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/conversations` | Create conversation |
| GET | `/conversations` | List conversations |
| GET | `/conversations/{id}` | Get conversation with messages |
| DELETE | `/conversations/{id}` | Delete conversation + messages |
| POST | `/messages` | Create message |
| GET | `/conversations/{id}/messages` | Get messages for conversation |
| GET | `/health` | Health check |

---

## Out of Scope

- User authentication/authorization
- Multi-model support per message
- Message editing or deletion
- Conversation sharing/export
- Real-time collaboration
- File/image attachments
- Soft delete
- Token counting

---

## Implementation Notes

- Max 100 messages per conversation
- Context window: Last 10 messages sent to Ollama
- Hard delete for conversations (cascade to messages)
- Cache TTL: 1 hour (unchanged)
