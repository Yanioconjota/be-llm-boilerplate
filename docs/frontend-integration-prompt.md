# Frontend Integration Prompt: Ollama Chat Backend

> This document was generated to facilitate Angular 19+ frontend development.
> Copy this entire document into a new conversation to build the frontend.

---

## Project Context

A FastAPI microservices backend for an LLM chat application with:
- **Ollama** integration for local LLM inference
- **Redis** caching for response deduplication
- **MongoDB** persistence for conversations and messages
- **Server-Sent Events (SSE)** for real-time streaming responses
- Full conversation management with context window support

**Backend URL**: `http://localhost:8000` (development)
**API Base Path**: `/` (no prefix)

---

## API Specification

### Authentication

**Type**: None (open API for development)

### Endpoints

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| GET | `/` | - | - | `HealthResponse` | Health check |
| POST | `/conversations` | - | `CreateConversationRequest` | `Conversation` | Create conversation |
| GET | `/conversations` | - | Query: `limit`, `offset` | `ConversationList` | List conversations |
| GET | `/conversations/{id}` | - | - | `ConversationWithMessages` | Get conversation + messages |
| DELETE | `/conversations/{id}` | - | - | `{ success: boolean }` | Delete conversation |
| POST | `/conversations/{id}/stream` | - | `StreamRequest` | SSE stream | Stream LLM response |

### Pagination Pattern

```typescript
interface ConversationList {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}
```

Default: `limit=20`, `offset=0`. Max limit: 100.

### Error Response Format

```typescript
interface ApiError {
  detail: string;
}
```

HTTP status codes:
- `400` - Bad request / Validation error
- `404` - Resource not found
- `500` - Internal server error

---

## TypeScript Interfaces

```typescript
// ============================================
// Domain Models
// ============================================

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;   // ISO 8601
  updated_at: string;   // ISO 8601
  model: string;        // e.g., "llama3"
  message_count: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;    // ISO 8601
  cached?: boolean;     // true if response was from Redis cache
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

// ============================================
// Request DTOs
// ============================================

export interface CreateConversationRequest {
  title?: string;       // Optional display title
  model?: string;       // Default: "llama3"
}

export interface StreamRequest {
  prompt: string;       // User's message text
}

// ============================================
// Response DTOs
// ============================================

export interface ConversationList {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface DeleteResponse {
  success: boolean;
}

// ============================================
// SSE Event Types
// ============================================

export interface SseChunkEvent {
  chunk: string;        // Token/word from LLM
  done: boolean;        // true on final event
  cached: boolean;      // true if from Redis cache
}

export interface SseErrorEvent {
  error: 'validation' | 'llm_unavailable' | 'timeout' | 'internal';
  message: string;
}

export type SseEvent = SseChunkEvent | SseErrorEvent;

// Type guard
export function isSseError(event: SseEvent): event is SseErrorEvent {
  return 'error' in event;
}
```

---

## Real-Time Features (SSE)

**SSE Endpoint**: `POST /conversations/{id}/stream`

This is NOT a standard EventSource-compatible endpoint (requires POST body), so use `fetch` with streaming.

### Event Format

```
event: message
data: {"chunk": "Hello", "done": false, "cached": false}

event: message
data: {"chunk": " world", "done": false, "cached": false}

event: message
data: {"chunk": "", "done": true, "cached": false}
```

### Error Events

```
event: error
data: {"error": "llm_unavailable", "message": "Cannot connect to Ollama"}

event: error
data: {"error": "timeout", "message": "Request timed out"}
```

### SSE Parsing Pattern

```typescript
async function parseSSE(response: Response, onChunk: (chunk: string) => void): Promise<SseChunkEvent> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalEvent: SseChunkEvent | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('event:')) continue; // Skip event type lines
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim();
        if (jsonStr) {
          const event: SseEvent = JSON.parse(jsonStr);
          
          if (isSseError(event)) {
            throw new Error(event.message);
          }
          
          if (event.chunk) {
            onChunk(event.chunk);
          }
          
          if (event.done) {
            finalEvent = event;
          }
        }
      }
    }
  }

  return finalEvent!;
}
```

---

## Business Rules & Constraints

| Rule | Value |
|------|-------|
| Max messages per conversation | 100 |
| Context window (sent to LLM) | Last 10 messages |
| Cache TTL | 1 hour |
| Supported model | `llama3` (default) |

When a conversation reaches 100 messages, the API returns:
```json
{
  "detail": "Conversation has reached the maximum of 100 messages. Please start a new conversation."
}
```

---

## Suggested Frontend Architecture

### Project Structure

```
src/app/
├── core/
│   ├── services/
│   │   ├── api.service.ts           # Base HTTP config
│   │   └── conversation.service.ts  # Conversation CRUD
│   └── interceptors/
│       └── error.interceptor.ts     # Global error handling
├── features/
│   └── chat/
│       ├── services/
│       │   └── sse-chat.service.ts  # SSE streaming
│       ├── store/
│       │   └── chat.store.ts        # NgRx Signal Store
│       ├── components/
│       │   ├── chat-container/
│       │   ├── message-list/
│       │   ├── message-bubble/
│       │   ├── chat-input/
│       │   └── conversation-sidebar/
│       └── chat.routes.ts
└── shared/
    ├── models/
    │   └── conversation.models.ts   # All interfaces
    └── ui/
        └── typing-indicator/
```

### Signal Store State Shape

```typescript
interface ChatState {
  // Conversations list
  conversations: Conversation[];
  conversationsLoading: boolean;
  conversationsError: string | null;
  
  // Active conversation
  activeConversationId: string | null;
  activeConversation: ConversationWithMessages | null;
  
  // Streaming state
  streamingChunks: string[];
  isStreaming: boolean;
  streamError: string | null;
  lastResponseCached: boolean;
}
```

---

## Instructions for Frontend Development

Build an Angular 19+ frontend following these requirements:

### Required Patterns

1. **Standalone components** - All components must be standalone
2. **Signal inputs/outputs** - Use `input()`, `output()`, `model()` instead of decorators
3. **Control flow** - Use `@if`, `@for`, `@switch` instead of `*ngIf`, `*ngFor`
4. **inject()** - Use `inject()` function for dependency injection
5. **Signal Store** - Use NgRx Signal Store for state management
6. **OnPush** - All components use `ChangeDetectionStrategy.OnPush`

### UI Framework

- **NgZorro** as primary design system
- **Angular Material** only when NgZorro lacks equivalent
- **Bootstrap** utilities for layout/spacing only

### HTTP Setup

```typescript
// app.config.ts
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { errorInterceptor } from './core/interceptors/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([errorInterceptor]),
      withFetch()
    ),
    // ... other providers
  ]
};
```

### Error Interceptor Pattern

```typescript
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const message = error.error?.detail || error.message || 'An error occurred';
      console.error('API Error:', message);
      return throwError(() => new Error(message));
    })
  );
};
```

### SSE Service Pattern

```typescript
@Injectable({ providedIn: 'root' })
export class SseChatService {
  private abortController: AbortController | null = null;
  
  readonly chunks = signal<string[]>([]);
  readonly isStreaming = signal(false);
  readonly error = signal<string | null>(null);
  readonly cached = signal(false);
  
  readonly fullResponse = computed(() => this.chunks().join(''));

  async streamMessage(conversationId: string, prompt: string): Promise<void> {
    this.reset();
    this.isStreaming.set(true);
    this.abortController = new AbortController();

    try {
      const response = await fetch(
        `http://localhost:8000/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
          signal: this.abortController.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Parse SSE stream...
      await this.parseStream(response);
      
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        this.error.set((err as Error).message);
      }
    } finally {
      this.isStreaming.set(false);
      this.abortController = null;
    }
  }

  cancelStream(): void {
    this.abortController?.abort();
  }

  private reset(): void {
    this.chunks.set([]);
    this.error.set(null);
    this.cached.set(false);
  }
}
```

### Accessibility Requirements

1. **ARIA live regions** for streaming responses:
   ```html
   <div aria-live="polite" aria-atomic="false" class="sr-only">
     {{ fullResponse() }}
   </div>
   ```

2. **Loading states** with proper announcements
3. **Focus management** after actions
4. **Keyboard navigation** for conversation list

---

## Development Checklist

- [ ] Set up Angular 19+ project with standalone components
- [ ] Configure HTTP client with error interceptor
- [ ] Create TypeScript interfaces from spec above
- [ ] Implement ConversationService for CRUD operations
- [ ] Implement SseChatService for SSE streaming
- [ ] Create NgRx Signal Store for chat state
- [ ] Build conversation list sidebar component
- [ ] Build message list with message bubbles
- [ ] Build chat input with send/cancel buttons
- [ ] Add typing indicator during streaming
- [ ] Add loading states and error handling
- [ ] Add "cached" badge for cached responses
- [ ] Implement conversation deletion
- [ ] Add responsive layout for mobile
- [ ] Add ARIA live regions for accessibility

---

## Testing the Backend

Before building the frontend, verify the backend is running:

```bash
# 1. Start Ollama
ollama serve

# 2. Start backend services
docker-compose up --build

# 3. Test health
curl http://localhost:8000/

# 4. Create conversation
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}'

# 5. Stream message (replace {id} with conversation ID)
curl -N -X POST "http://localhost:8000/conversations/{id}/stream" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

Swagger UI: http://localhost:8000/docs
