# Frontend Integration: Ollama Chat - User Story

## Overview

Build an Angular 19+ frontend for a local LLM chat application powered by Ollama, featuring real-time streaming responses and full conversation management.

---

## Project Context

A FastAPI microservices backend for an LLM chat application featuring:

- **Ollama** integration for local LLM inference (llama3 model)
- **Redis** caching for response deduplication (1 hour TTL)
- **MongoDB** persistence for conversations and messages
- **Server-Sent Events (SSE)** for real-time streaming responses
- Full conversation management with context window support (last 10 messages)

---

## User Persona

### Primary User: Developer/Power User
- Wants to interact with a local LLM through a clean chat interface
- Values seeing responses stream in real-time (token by token)
- Needs to manage multiple conversation threads
- Appreciates knowing when responses come from cache vs fresh generation

---

## User Story

**As a user, I want to chat with a local LLM through a web interface**
so that I can have conversations with AI, manage multiple chat threads, and see responses stream in real-time.

### Acceptance Criteria

#### Conversation Management
- [ ] Create new conversations by clicking "New Chat"
- [ ] View conversation history in a sidebar sorted by most recent
- [ ] Delete conversations with confirmation prompt
- [ ] Switch between conversations and see messages load

#### Chat Interaction
- [ ] Send messages and see streaming responses token by token
- [ ] Cancel streaming responses mid-generation
- [ ] See "cached" badge when response comes from cache
- [ ] See typing indicator while waiting for response
- [ ] Handle errors with user-friendly messages
- [ ] See loading states for all async operations

---

## Business Rules & Constraints

| Rule | Value |
|------|-------|
| Max messages per conversation | 100 |
| Context window (sent to LLM) | Last 10 messages |
| Cache TTL | 1 hour (3600s) |
| Default model | `llama3` |
| Empty prompts | Not allowed (400 error) |

---

## UI/UX Requirements

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  Header: App Title / Logo                                       │
├─────────────────┬───────────────────────────────────────────────┤
│                 │                                               │
│  Conversation   │  Chat Messages Area                           │
│  List           │                                               │
│                 │  ┌─────────────────────────────────────────┐  │
│  [+ New Chat]   │  │ User: Hello                             │  │
│                 │  └─────────────────────────────────────────┘  │
│  Chat 1     ◄── │  ┌─────────────────────────────────────────┐  │
│  Chat 2         │  │ Assistant: Hi! How can I help? [cached] │  │
│  Chat 3         │  └─────────────────────────────────────────┘  │
│                 │                                               │
│                 │  ┌─────────────────────────────────────────┐  │
│                 │  │ ● ● ●  (typing indicator)               │  │
│                 │  └─────────────────────────────────────────┘  │
│                 │                                               │
│                 ├───────────────────────────────────────────────┤
│                 │  [Message input...        ] [Send] [Cancel]   │
└─────────────────┴───────────────────────────────────────────────┘
```

### Visual Feedback States

| State | Visual Indicator |
|-------|------------------|
| Loading conversations | Skeleton/spinner in sidebar |
| Loading messages | Spinner in chat area |
| Streaming response | Typing indicator + text appearing |
| Cached response | Blue "cached" badge on message |
| Error | Red notification/toast |
| Empty state | Illustration + "Start a conversation" |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line in message |
| `Escape` | Cancel streaming (when active) |

---

## Scope

### Must Have (MVP)
- [ ] Create new conversations
- [ ] List all conversations
- [ ] Delete conversations
- [ ] Send messages with SSE streaming
- [ ] Display messages with user/assistant styling
- [ ] Show typing indicator during streaming
- [ ] Cancel streaming responses
- [ ] Show cached badge on cached responses
- [ ] Error handling with user-friendly messages
- [ ] Loading states for all async operations

### Should Have
- [ ] Responsive layout for mobile
- [ ] Message timestamps

---

## Development Checklist

### Setup
- [ ] Set up Angular 19+ project with standalone components
- [ ] Install dependencies: `@ngrx/signals`, `ng-zorro-antd`, `bootstrap`
- [ ] Configure HTTP client with error interceptor

### Data Layer
- [ ] Create TypeScript interfaces from API spec
- [ ] Implement ConversationApiService for CRUD operations
- [ ] Implement SseStreamService for SSE streaming
- [ ] Create NgRx Signal Store for chat state

### UI Components
- [ ] Build conversation list sidebar component
- [ ] Build message list with message bubbles
- [ ] Build chat input with send/cancel buttons
- [ ] Add typing indicator during streaming
- [ ] Add streaming text display (real-time chunks)

### UX Polish
- [ ] Add loading states and error handling
- [ ] Add "cached" badge for cached responses
- [ ] Implement conversation creation modal
- [ ] Implement conversation deletion with confirmation
- [ ] Add responsive layout for mobile
- [ ] Add empty state when no conversations exist

---

## Testing the Backend

Before building the frontend, verify the backend is running:

```bash
# 1. Start Ollama (required for LLM)
ollama serve

# 2. Start backend services
docker-compose up --build

# 3. Test health endpoint
curl http://localhost:8000/

# 4. Create a conversation
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'

# 5. Stream a message (replace {id} with actual conversation ID)
curl -N -X POST "http://localhost:8000/conversations/{id}/stream" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

**Swagger UI**: http://localhost:8000/docs

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to first message sent | < 30 seconds from landing |
| Streaming responsiveness | First token visible < 500ms |
| Error recovery | User can retry after any error |
