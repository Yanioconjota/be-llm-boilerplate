# Frontend Integration: Ollama Chat - Technical Specification

## Environment Setup

| Service | URL | Purpose |
|---------|-----|---------|
| FastAPI Gateway | http://localhost:8000 | Main API (frontend connects here) |
| Swagger Docs | http://localhost:8000/docs | API documentation |
| Storage Service | http://localhost:8001 | Internal (MongoDB persistence) |
| MongoDB | localhost:27017 | Database |
| Redis | localhost:6379 | Response cache |
| RedisInsight | http://localhost:8002 | Redis GUI |

---

## API Specification

### Authentication

**Type**: None (open API for development)

> Note: No authentication headers required. CORS is configured to allow all origins.

### Endpoints

| Method | Path | Request Body | Query Params | Response | Description |
|--------|------|--------------|--------------|----------|-------------|
| GET | `/` | - | - | `HealthResponse` | Health check |
| POST | `/conversations` | `CreateConversationRequest` | - | `Conversation` | Create new conversation |
| GET | `/conversations` | - | `limit`, `offset` | `ConversationList` | List conversations (paginated) |
| GET | `/conversations/{id}` | - | - | `ConversationWithMessages` | Get conversation with all messages |
| DELETE | `/conversations/{id}` | - | - | `DeleteResponse` | Delete conversation and messages |
| POST | `/conversations/{id}/stream` | `StreamRequest` | - | SSE stream | Send message & stream LLM response |
| POST | `/ask` | `PromptRequest` | - | `AskResponse` | Stateless prompt (no conversation context) |

### Pagination Pattern

```typescript
interface PaginationParams {
  limit?: number;  // Default: 20, Min: 1, Max: 100
  offset?: number; // Default: 0, Min: 0
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

### Error Response Format

```typescript
interface ApiError {
  detail: string;
}
```

HTTP status codes:
- `400` - Bad request / Validation error / Message limit reached
- `404` - Conversation not found
- `500` - Internal server error / Database error

---

## TypeScript Interfaces

```typescript
// ============================================
// Domain Models
// ============================================

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  model: string;
  message_count: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  cached?: boolean;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

// ============================================
// Request DTOs
// ============================================

export interface CreateConversationRequest {
  title?: string;
  model?: string;
}

export interface StreamRequest {
  prompt: string;
}

export interface PromptRequest {
  prompt: string;
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

export interface AskResponse {
  response: string;
  cached: boolean;
}

// ============================================
// SSE Event Types
// ============================================

export interface SseChunkEvent {
  chunk: string;
  done: boolean;
  cached: boolean;
}

export interface SseErrorEvent {
  error: 'validation' | 'llm_unavailable' | 'timeout' | 'internal';
  message: string;
}

export type SseEvent = SseChunkEvent | SseErrorEvent;

export function isSseError(event: SseEvent): event is SseErrorEvent {
  return 'error' in event;
}

export function isSseChunk(event: SseEvent): event is SseChunkEvent {
  return 'chunk' in event;
}
```

---

## SSE Streaming Protocol

**Endpoint**: `POST /conversations/{id}/stream`

> **Important**: This is NOT a standard EventSource-compatible endpoint because it requires a POST body.
> Use `fetch` API with streaming instead of `EventSource`.

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

---

## Suggested Project Structure

```
src/app/
├── app.component.ts
├── app.config.ts
├── app.routes.ts
├── core/
│   ├── interceptors/
│   │   └── error.interceptor.ts
│   ├── services/
│   │   └── api-base.service.ts
│   └── utils/
│       └── sse-parser.util.ts
├── features/
│   └── chat/
│       ├── chat.routes.ts
│       ├── services/
│       │   ├── conversation-api.service.ts
│       │   └── sse-stream.service.ts
│       ├── store/
│       │   └── chat.store.ts
│       ├── components/
│       │   ├── chat-container/
│       │   ├── conversation-list/
│       │   ├── message-list/
│       │   ├── message-bubble/
│       │   ├── chat-input/
│       │   └── typing-indicator/
│       └── pages/
│           └── chat-page/
└── shared/
    ├── models/
    │   ├── conversation.model.ts
    │   ├── message.model.ts
    │   └── sse-event.model.ts
    └── components/
        └── loading-spinner/
```

---

## Angular Configuration

### App Configuration

```typescript
// app.config.ts
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { routes } from './app.routes';
import { errorInterceptor } from './core/interceptors/error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([errorInterceptor]), withFetch()),
    provideAnimationsAsync(),
  ],
};
```

### Error Interceptor

```typescript
// core/interceptors/error.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let message = 'An unexpected error occurred';

      if (error.error?.detail) {
        message = error.error.detail;
      } else if (error.status === 0) {
        message = 'Unable to connect to server. Please check if the backend is running.';
      } else if (error.status === 404) {
        message = 'Resource not found';
      } else if (error.status >= 500) {
        message = 'Server error. Please try again later.';
      }

      console.error('API Error:', { status: error.status, message });
      return throwError(() => new Error(message));
    })
  );
};
```

---

## Service Implementations

### Conversation API Service

```typescript
// features/chat/services/conversation-api.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Conversation,
  ConversationWithMessages,
  ConversationList,
  CreateConversationRequest,
  DeleteResponse,
} from '../../../shared/models';

@Injectable({ providedIn: 'root' })
export class ConversationApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  create(request: CreateConversationRequest = {}): Observable<Conversation> {
    return this.http.post<Conversation>(`${this.baseUrl}/conversations`, request);
  }

  list(limit = 20, offset = 0): Observable<ConversationList> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<ConversationList>(`${this.baseUrl}/conversations`, { params });
  }

  get(id: string): Observable<ConversationWithMessages> {
    return this.http.get<ConversationWithMessages>(`${this.baseUrl}/conversations/${id}`);
  }

  delete(id: string): Observable<DeleteResponse> {
    return this.http.delete<DeleteResponse>(`${this.baseUrl}/conversations/${id}`);
  }
}
```

### SSE Stream Service

```typescript
// features/chat/services/sse-stream.service.ts
import { Injectable } from '@angular/core';
import { SseEvent, isSseError } from '../../../shared/models';

interface StreamResult {
  fullResponse: string;
  cached: boolean;
}

@Injectable({ providedIn: 'root' })
export class SseStreamService {
  private readonly baseUrl = 'http://localhost:8000';
  private abortController: AbortController | null = null;

  async streamMessage(
    conversationId: string,
    prompt: string,
    onChunk: (chunk: string) => void
  ): Promise<StreamResult> {
    this.abortController = new AbortController();
    let fullResponse = '';
    let cached = false;

    try {
      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
          signal: this.abortController.signal,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr) {
              const event: SseEvent = JSON.parse(jsonStr);

              if (isSseError(event)) {
                throw new Error(event.message);
              }

              if (event.chunk) {
                fullResponse += event.chunk;
                onChunk(event.chunk);
              }

              if (event.done) {
                cached = event.cached;
              }
            }
          }
        }
      }

      return { fullResponse, cached };
    } finally {
      this.abortController = null;
    }
  }

  cancel(): void {
    this.abortController?.abort();
    this.abortController = null;
  }
}
```

---

## NgRx Signal Store Implementation

```typescript
// features/chat/store/chat.store.ts
import { computed, inject } from '@angular/core';
import {
  patchState,
  signalStore,
  withComputed,
  withMethods,
  withState,
} from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';
import { ConversationApiService } from '../services/conversation-api.service';
import { SseStreamService } from '../services/sse-stream.service';
import {
  Conversation,
  ConversationWithMessages,
  Message,
} from '../../../shared/models';

interface ChatState {
  conversations: Conversation[];
  conversationsLoading: boolean;
  conversationsError: string | null;

  activeConversationId: string | null;
  activeConversation: ConversationWithMessages | null;
  activeConversationLoading: boolean;

  streamingChunks: string[];
  isStreaming: boolean;
  streamError: string | null;
  lastResponseCached: boolean;
}

const initialState: ChatState = {
  conversations: [],
  conversationsLoading: false,
  conversationsError: null,
  activeConversationId: null,
  activeConversation: null,
  activeConversationLoading: false,
  streamingChunks: [],
  isStreaming: false,
  streamError: null,
  lastResponseCached: false,
};

export const ChatStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed((store) => ({
    streamingResponse: computed(() => store.streamingChunks().join('')),
    hasActiveConversation: computed(() => store.activeConversationId() !== null),
    activeMessages: computed(() => store.activeConversation()?.messages ?? []),
    canSendMessage: computed(
      () => !store.isStreaming() && store.hasActiveConversation()
    ),
  })),
  withMethods(
    (
      store,
      conversationApi = inject(ConversationApiService),
      sseStream = inject(SseStreamService)
    ) => ({
      loadConversations: rxMethod<{ limit?: number; offset?: number }>(
        pipe(
          tap(() =>
            patchState(store, { conversationsLoading: true, conversationsError: null })
          ),
          switchMap(({ limit = 20, offset = 0 }) =>
            conversationApi.list(limit, offset).pipe(
              tapResponse({
                next: (response) =>
                  patchState(store, {
                    conversations: response.items,
                    conversationsLoading: false,
                  }),
                error: (error: Error) =>
                  patchState(store, {
                    conversationsError: error.message,
                    conversationsLoading: false,
                  }),
              })
            )
          )
        )
      ),

      createConversation: rxMethod<{ title?: string; model?: string }>(
        pipe(
          switchMap((request) =>
            conversationApi.create(request).pipe(
              tapResponse({
                next: (conversation) => {
                  patchState(store, {
                    conversations: [conversation, ...store.conversations()],
                    activeConversationId: conversation.id,
                    activeConversation: { ...conversation, messages: [] },
                  });
                },
                error: (error: Error) =>
                  patchState(store, { conversationsError: error.message }),
              })
            )
          )
        )
      ),

      selectConversation: rxMethod<string>(
        pipe(
          tap((id) =>
            patchState(store, {
              activeConversationId: id,
              activeConversationLoading: true,
            })
          ),
          switchMap((id) =>
            conversationApi.get(id).pipe(
              tapResponse({
                next: (conversation) =>
                  patchState(store, {
                    activeConversation: conversation,
                    activeConversationLoading: false,
                  }),
                error: (error: Error) =>
                  patchState(store, {
                    conversationsError: error.message,
                    activeConversationLoading: false,
                  }),
              })
            )
          )
        )
      ),

      deleteConversation: rxMethod<string>(
        pipe(
          switchMap((id) =>
            conversationApi.delete(id).pipe(
              tapResponse({
                next: () => {
                  const isActive = store.activeConversationId() === id;
                  patchState(store, {
                    conversations: store.conversations().filter((c) => c.id !== id),
                    ...(isActive && {
                      activeConversationId: null,
                      activeConversation: null,
                    }),
                  });
                },
                error: (error: Error) =>
                  patchState(store, { conversationsError: error.message }),
              })
            )
          )
        )
      ),

      async sendMessage(prompt: string): Promise<void> {
        const conversationId = store.activeConversationId();
        if (!conversationId || store.isStreaming()) return;

        // Add user message optimistically
        const userMessage: Message = {
          id: crypto.randomUUID(),
          conversation_id: conversationId,
          role: 'user',
          content: prompt,
          timestamp: new Date().toISOString(),
        };

        patchState(store, {
          activeConversation: {
            ...store.activeConversation()!,
            messages: [...store.activeMessages(), userMessage],
            message_count: store.activeConversation()!.message_count + 1,
          },
          streamingChunks: [],
          isStreaming: true,
          streamError: null,
          lastResponseCached: false,
        });

        try {
          const result = await sseStream.streamMessage(
            conversationId,
            prompt,
            (chunk) => {
              patchState(store, {
                streamingChunks: [...store.streamingChunks(), chunk],
              });
            }
          );

          // Add assistant message when done
          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            conversation_id: conversationId,
            role: 'assistant',
            content: store.streamingResponse(),
            timestamp: new Date().toISOString(),
            cached: result.cached,
          };

          patchState(store, {
            activeConversation: {
              ...store.activeConversation()!,
              messages: [...store.activeMessages(), assistantMessage],
              message_count: store.activeConversation()!.message_count + 1,
              updated_at: new Date().toISOString(),
            },
            streamingChunks: [],
            isStreaming: false,
            lastResponseCached: result.cached,
          });
        } catch (error) {
          patchState(store, {
            streamError: (error as Error).message,
            isStreaming: false,
          });
        }
      },

      cancelStream(): void {
        sseStream.cancel();
        patchState(store, { isStreaming: false });
      },

      clearStreamError(): void {
        patchState(store, { streamError: null });
      },
    })
  )
);
```

---

## Component Examples

### Chat Input Component

```typescript
// features/chat/components/chat-input/chat-input.component.ts
import { Component, inject, output, input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [FormsModule, NzInputModule, NzButtonModule, NzIconModule],
  template: `
    <form (ngSubmit)="handleSubmit()" class="chat-input-form">
      <nz-input-group [nzSuffix]="suffixTemplate">
        <textarea
          nz-input
          [(ngModel)]="messageText"
          name="message"
          placeholder="Type your message..."
          [nzAutosize]="{ minRows: 1, maxRows: 4 }"
          [disabled]="disabled()"
          (keydown.enter)="handleKeydown($event)"
        ></textarea>
      </nz-input-group>

      <ng-template #suffixTemplate>
        @if (isStreaming()) {
          <button
            nz-button
            nzType="default"
            nzDanger
            type="button"
            (click)="cancel.emit()"
          >
            <nz-icon nzType="stop" />
            Cancel
          </button>
        } @else {
          <button
            nz-button
            nzType="primary"
            type="submit"
            [disabled]="disabled() || !messageText.trim()"
          >
            <nz-icon nzType="send" />
            Send
          </button>
        }
      </ng-template>
    </form>
  `,
})
export class ChatInputComponent {
  readonly disabled = input(false);
  readonly isStreaming = input(false);

  readonly send = output<string>();
  readonly cancel = output<void>();

  messageText = '';

  handleSubmit(): void {
    const text = this.messageText.trim();
    if (text && !this.disabled()) {
      this.send.emit(text);
      this.messageText = '';
    }
  }

  handleKeydown(event: KeyboardEvent): void {
    if (!event.shiftKey) {
      event.preventDefault();
      this.handleSubmit();
    }
  }
}
```

### Message Bubble Component

```typescript
// features/chat/components/message-bubble/message-bubble.component.ts
import { Component, input, computed } from '@angular/core';
import { DatePipe } from '@angular/common';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { Message } from '../../../../shared/models';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [DatePipe, NzTagModule],
  template: `
    <div [class]="bubbleClass()">
      <div class="message-content">
        <p class="message-text">{{ message().content }}</p>
        <div class="message-meta">
          <span class="timestamp">{{ message().timestamp | date:'shortTime' }}</span>
          @if (message().cached) {
            <nz-tag nzColor="blue">cached</nz-tag>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .message-bubble {
      max-width: 80%;
      padding: 12px 16px;
      border-radius: 12px;
      margin-bottom: 8px;
    }
    .message-bubble--user {
      background: #1890ff;
      color: white;
      margin-left: auto;
      border-bottom-right-radius: 4px;
    }
    .message-bubble--assistant {
      background: #f5f5f5;
      color: #333;
      margin-right: auto;
      border-bottom-left-radius: 4px;
    }
    .message-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
      font-size: 12px;
      opacity: 0.7;
    }
  `],
})
export class MessageBubbleComponent {
  readonly message = input.required<Message>();

  readonly bubbleClass = computed(
    () => `message-bubble message-bubble--${this.message().role}`
  );
}
```

### Typing Indicator Component

```typescript
// features/chat/components/typing-indicator/typing-indicator.component.ts
import { Component } from '@angular/core';

@Component({
  selector: 'app-typing-indicator',
  standalone: true,
  template: `
    <div class="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `,
  styles: [`
    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
      background: #f5f5f5;
      border-radius: 12px;
      width: fit-content;
    }
    .typing-indicator span {
      width: 8px;
      height: 8px;
      background: #999;
      border-radius: 50%;
      animation: bounce 1.4s infinite ease-in-out;
    }
    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
  `],
})
export class TypingIndicatorComponent {}
```

---

## Required Angular Patterns

1. **Standalone components** - All components must be standalone (`standalone: true`)
2. **Signal inputs/outputs** - Use `input()`, `input.required()`, `output()`, `model()` instead of decorators
3. **Control flow** - Use `@if`, `@for`, `@switch` instead of `*ngIf`, `*ngFor`
4. **inject()** - Use `inject()` function for dependency injection
5. **Signal Store** - Use NgRx Signal Store (`@ngrx/signals`) for state management

### UI Framework Priority

1. **NgZorro** as primary design system (tables, forms, modals, notifications)
2. **Angular Material** only when NgZorro lacks equivalent (document the reason)
3. **Bootstrap** utilities for layout/spacing only (`d-flex`, `gap-3`, `p-4`, etc.)

### Accessibility Requirements

1. **ARIA live regions** for streaming responses
2. **Focus management** after actions
3. **Keyboard navigation** for conversation list
4. **Loading state announcements**

---

## Dependencies

```json
{
  "dependencies": {
    "@angular/core": "^19.0.0",
    "@ngrx/signals": "^19.0.0",
    "ng-zorro-antd": "^19.0.0",
    "bootstrap": "^5.3.0"
  }
}
```
