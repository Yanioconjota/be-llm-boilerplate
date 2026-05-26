# Microservices Backend with Ollama LLM

A complete FastAPI microservices backend with Redis caching, MongoDB persistence, Ollama LLM integration, and **Server-Sent Events (SSE)** for streaming responses.

## Architecture

```
┌──────────────────┐     ┌───────────────────┐
│   FastAPI        │────▶│   Redis Cache     │
│   (Port 8000)    │     │   (Port 6379)     │
└────────┬─────────┘     └───────────────────┘
         │
         │ Cache MISS
         ▼
┌───────────────────┐
│   Ollama (Host)   │
│   (Port 11434)    │
└───────────────────┘
         │
         ▼
┌──────────────────┐     ┌───────────────────┐
│ Storage Service  │────▶│   MongoDB         │
│   (Port 8001)    │     │   (Port 27017)    │
└──────────────────┘     └───────────────────┘
```

**Flow (Conversations)**:
1. Client creates a conversation via `POST /conversations`
2. Client sends prompt to `POST /conversations/{id}/stream`
3. User message is stored
4. FastAPI checks Redis cache (HIT → stream cached response)
5. On MISS → stream from Ollama with conversation context → cache response → store assistant message
6. Response streams via Server-Sent Events (SSE)

## Prerequisites

1. **Docker Desktop** installed and running
2. **Ollama** installed on host machine:
   ```bash
   # Install from https://ollama.com
   ollama pull llama3
   ollama serve
   ```

## Project Structure

```
project-root/
├── docker-compose.yml
├── specs/
│   └── sse-conversations.spec.md   # Feature specification
├── fast-api/
│   ├── app/
│   │   └── main.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   └── forward.py
│   ├── .env.template
│   ├── Dockerfile
│   └── requirements.txt
└── chat-storage-service/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── database.py
    │   ├── models.py
    │   └── routes/
    │       ├── __init__.py
    │       ├── save.py
    │       ├── conversations.py
    │       └── messages.py
    ├── .env.template
    ├── Dockerfile
    └── requirements.txt
```

## Quick Start

1. **Clone the repository**

2. **Create environment files from templates**:
   ```bash
   cp fast-api/.env.template fast-api/.env
   cp chat-storage-service/.env.template chat-storage-service/.env
   ```

3. **Start Ollama on your host machine**:
   ```bash
   ollama serve
   ```

4. **Start all services**:
   ```bash
   docker-compose up --build
   ```

## Service URLs

| Service | URL |
|---------|-----|
| FastAPI Swagger | http://localhost:8000/docs |
| FastAPI ReDoc | http://localhost:8000/redoc |
| Storage Health | http://localhost:8001/health |
| RedisInsight UI | http://localhost:8002 |

## API Endpoints

### FastAPI (Port 8000)

#### Health & Legacy Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/joker` | Demo: get a joke from Ollama |
| POST | `/ask` | Stateless prompt (no conversation context) |

#### Conversation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/conversations` | Create a new conversation |
| GET | `/conversations` | List all conversations (paginated) |
| GET | `/conversations/{id}` | Get conversation with all messages |
| DELETE | `/conversations/{id}` | Delete conversation and messages |
| POST | `/conversations/{id}/stream` | Send message & stream response (SSE) |

### Storage Service (Port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/save` | Legacy: Save prompt/response pair |
| GET | `/health` | Check MongoDB connection |
| POST | `/conversations` | Create conversation |
| GET | `/conversations` | List conversations |
| GET | `/conversations/{id}` | Get conversation with messages |
| DELETE | `/conversations/{id}` | Delete conversation |
| POST | `/messages` | Create message |
| GET | `/conversations/{id}/messages` | Get messages |

## Usage Examples

### Create a Conversation

```bash
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat", "model": "llama3"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Chat",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00",
  "model": "llama3",
  "message_count": 0
}
```

### List Conversations

```bash
curl "http://localhost:8000/conversations?limit=10&offset=0"
```

### Get Conversation with Messages

```bash
curl http://localhost:8000/conversations/{conversation_id}
```

### Stream a Message (SSE)

```bash
curl -N -X POST "http://localhost:8000/conversations/{id}/stream" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

Response (Server-Sent Events):
```
event: message
data: {"chunk": "Hello", "done": false, "cached": false}

event: message
data: {"chunk": "!", "done": false, "cached": false}

event: message
data: {"chunk": " I", "done": false, "cached": false}

...

event: message
data: {"chunk": "", "done": true, "cached": false}
```

### Delete a Conversation

```bash
curl -X DELETE http://localhost:8000/conversations/{id}
```

## SSE Event Format

### Success Events

```
event: message
data: {"chunk": "token text", "done": false, "cached": false}

event: message
data: {"chunk": "", "done": true, "cached": false}
```

### Error Events

```
event: error
data: {"error": "llm_unavailable", "message": "Cannot connect to Ollama"}

event: error
data: {"error": "timeout", "message": "Request timed out"}

event: error
data: {"error": "internal", "message": "An error occurred"}
```

---

## Frontend Integration

### TypeScript Interfaces

```typescript
// models/conversation.models.ts

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

export interface ConversationList {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateConversationRequest {
  title?: string;
  model?: string;
}

export interface StreamRequest {
  prompt: string;
}

// SSE Event types
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
```

---

## Angular Integration

### Conversation Service

```typescript
// services/conversation.service.ts
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Conversation,
  ConversationWithMessages,
  ConversationList,
  CreateConversationRequest
} from '../models/conversation.models';

@Injectable({ providedIn: 'root' })
export class ConversationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  create(request: CreateConversationRequest = {}): Observable<Conversation> {
    return this.http.post<Conversation>(`${this.baseUrl}/conversations`, request);
  }

  list(limit = 20, offset = 0): Observable<ConversationList> {
    return this.http.get<ConversationList>(
      `${this.baseUrl}/conversations`,
      { params: { limit, offset } }
    );
  }

  get(id: string): Observable<ConversationWithMessages> {
    return this.http.get<ConversationWithMessages>(
      `${this.baseUrl}/conversations/${id}`
    );
  }

  delete(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(
      `${this.baseUrl}/conversations/${id}`
    );
  }
}
```

### SSE Streaming Service

```typescript
// services/sse-chat.service.ts
import { Injectable, inject, signal, computed } from '@angular/core';
import { SseEvent, SseChunkEvent, isSseError } from '../models/conversation.models';
import { ConversationService } from './conversation.service';

@Injectable({ providedIn: 'root' })
export class SseChatService {
  private readonly conversationService = inject(ConversationService);
  private readonly baseUrl = 'http://localhost:8000';
  
  private abortController: AbortController | null = null;

  readonly chunks = signal<string[]>([]);
  readonly isStreaming = signal(false);
  readonly error = signal<string | null>(null);
  readonly cached = signal(false);

  readonly fullResponse = computed(() => this.chunks().join(''));

  async streamMessage(conversationId: string, prompt: string): Promise<void> {
    // Reset state
    this.chunks.set([]);
    this.error.set(null);
    this.isStreaming.set(true);
    this.cached.set(false);

    // Create abort controller for cancellation
    this.abortController = new AbortController();

    try {
      const response = await fetch(
        `${this.baseUrl}/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
          signal: this.abortController.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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
            const jsonStr = line.slice(6);
            if (jsonStr.trim()) {
              const event: SseEvent = JSON.parse(jsonStr);
              
              if (isSseError(event)) {
                this.error.set(event.message);
                this.isStreaming.set(false);
                return;
              }

              const chunk = event as SseChunkEvent;
              if (chunk.chunk) {
                this.chunks.update(c => [...c, chunk.chunk]);
              }
              if (chunk.done) {
                this.cached.set(chunk.cached);
                this.isStreaming.set(false);
                return;
              }
            }
          }
        }
      }
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
    this.isStreaming.set(false);
  }

  clearResponse(): void {
    this.chunks.set([]);
    this.error.set(null);
    this.cached.set(false);
  }
}
```

### Chat Component Example

```typescript
// components/chat.component.ts
import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConversationService } from '../services/conversation.service';
import { SseChatService } from '../services/sse-chat.service';
import { ConversationWithMessages, Message } from '../models/conversation.models';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="chat-container">
      <h2>Chat</h2>

      @if (!conversationId()) {
        <button (click)="startConversation()">Start New Conversation</button>
      } @else {
        <div class="messages">
          @for (message of messages(); track message.id) {
            <div [class]="'message message--' + message.role">
              <strong>{{ message.role }}:</strong>
              <p>{{ message.content }}</p>
            </div>
          }

          @if (sseChat.isStreaming() || sseChat.fullResponse()) {
            <div class="message message--assistant">
              <strong>assistant:</strong>
              <p>{{ sseChat.fullResponse() }}</p>
              @if (sseChat.isStreaming()) {
                <span class="typing-indicator">▌</span>
              }
            </div>
          }
        </div>

        @if (sseChat.error(); as error) {
          <div class="error" role="alert">{{ error }}</div>
        }

        <form (submit)="sendMessage($event)">
          <textarea
            [(ngModel)]="prompt"
            name="prompt"
            placeholder="Type your message..."
            rows="3"
            [disabled]="sseChat.isStreaming()"
          ></textarea>
          <button type="submit" [disabled]="sseChat.isStreaming() || !prompt.trim()">
            @if (sseChat.isStreaming()) {
              Streaming...
            } @else {
              Send
            }
          </button>
          @if (sseChat.isStreaming()) {
            <button type="button" (click)="sseChat.cancelStream()">Cancel</button>
          }
        </form>
      }
    </div>
  `
})
export class ChatComponent {
  protected readonly conversationService = inject(ConversationService);
  protected readonly sseChat = inject(SseChatService);

  protected conversationId = signal<string | null>(null);
  protected messages = signal<Message[]>([]);
  protected prompt = '';

  async startConversation(): Promise<void> {
    this.conversationService.create({ title: 'New Chat' }).subscribe({
      next: (conv) => this.conversationId.set(conv.id),
      error: (err) => console.error('Failed to create conversation:', err)
    });
  }

  async sendMessage(event: Event): Promise<void> {
    event.preventDefault();
    
    const prompt = this.prompt.trim();
    if (!prompt || !this.conversationId()) return;

    // Add user message to UI immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: this.conversationId()!,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString()
    };
    this.messages.update(m => [...m, userMessage]);
    this.prompt = '';

    // Stream response
    await this.sseChat.streamMessage(this.conversationId()!, prompt);

    // Add assistant message when done
    if (this.sseChat.fullResponse() && !this.sseChat.error()) {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        conversation_id: this.conversationId()!,
        role: 'assistant',
        content: this.sseChat.fullResponse(),
        timestamp: new Date().toISOString(),
        cached: this.sseChat.cached()
      };
      this.messages.update(m => [...m, assistantMessage]);
      this.sseChat.clearResponse();
    }
  }
}
```

---

## React + TypeScript Integration

### SSE Hook

```typescript
// hooks/useSseChat.ts
import { useState, useCallback, useRef } from 'react';
import { SseEvent, SseChunkEvent, isSseError } from '../models/conversation.models';

interface UseSseChatReturn {
  chunks: string[];
  fullResponse: string;
  isStreaming: boolean;
  error: string | null;
  cached: boolean;
  streamMessage: (conversationId: string, prompt: string) => Promise<void>;
  cancelStream: () => void;
  clearResponse: () => void;
}

export function useSseChat(): UseSseChatReturn {
  const [chunks, setChunks] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cached, setCached] = useState(false);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const streamMessage = useCallback(async (conversationId: string, prompt: string) => {
    setChunks([]);
    setError(null);
    setIsStreaming(true);
    setCached(false);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(
        `http://localhost:8000/conversations/${conversationId}/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
          signal: abortControllerRef.current.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
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
            const jsonStr = line.slice(6);
            if (jsonStr.trim()) {
              const event: SseEvent = JSON.parse(jsonStr);
              
              if (isSseError(event)) {
                setError(event.message);
                setIsStreaming(false);
                return;
              }

              const chunk = event as SseChunkEvent;
              if (chunk.chunk) {
                setChunks(prev => [...prev, chunk.chunk]);
              }
              if (chunk.done) {
                setCached(chunk.cached);
                setIsStreaming(false);
                return;
              }
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError((err as Error).message);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, []);

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const clearResponse = useCallback(() => {
    setChunks([]);
    setError(null);
    setCached(false);
  }, []);

  return {
    chunks,
    fullResponse: chunks.join(''),
    isStreaming,
    error,
    cached,
    streamMessage,
    cancelStream,
    clearResponse
  };
}
```

### Chat Component (React)

```tsx
// components/Chat.tsx
import { useState, FormEvent } from 'react';
import { useSseChat } from '../hooks/useSseChat';
import { Message } from '../models/conversation.models';

export function Chat() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [prompt, setPrompt] = useState('');
  
  const {
    fullResponse,
    isStreaming,
    error,
    cached,
    streamMessage,
    cancelStream,
    clearResponse
  } = useSseChat();

  const startConversation = async () => {
    const response = await fetch('http://localhost:8000/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'New Chat' })
    });
    const data = await response.json();
    setConversationId(data.id);
  };

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !conversationId) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: conversationId,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    const currentPrompt = prompt;
    setPrompt('');

    await streamMessage(conversationId, currentPrompt);

    if (fullResponse && !error) {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        conversation_id: conversationId,
        role: 'assistant',
        content: fullResponse,
        timestamp: new Date().toISOString(),
        cached
      };
      setMessages(prev => [...prev, assistantMessage]);
      clearResponse();
    }
  };

  return (
    <div className="chat-container">
      <h2>Chat</h2>

      {!conversationId ? (
        <button onClick={startConversation}>Start New Conversation</button>
      ) : (
        <>
          <div className="messages">
            {messages.map(msg => (
              <div key={msg.id} className={`message message--${msg.role}`}>
                <strong>{msg.role}:</strong>
                <p>{msg.content}</p>
              </div>
            ))}

            {(isStreaming || fullResponse) && (
              <div className="message message--assistant">
                <strong>assistant:</strong>
                <p>{fullResponse}</p>
                {isStreaming && <span className="typing-indicator">▌</span>}
              </div>
            )}
          </div>

          {error && <div className="error">{error}</div>}

          <form onSubmit={sendMessage}>
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="Type your message..."
              rows={3}
              disabled={isStreaming}
            />
            <button type="submit" disabled={isStreaming || !prompt.trim()}>
              {isStreaming ? 'Streaming...' : 'Send'}
            </button>
            {isStreaming && (
              <button type="button" onClick={cancelStream}>Cancel</button>
            )}
          </form>
        </>
      )}
    </div>
  );
}
```

---

## Environment Variables

### FastAPI Service

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | App display name | FastAPI App |
| `APP_ENV` | Environment | development |
| `APP_HOST` | Bind address | 0.0.0.0 |
| `APP_PORT` | Bind port | 8000 |
| `OLLAMA_HOST` | Ollama server | http://host.docker.internal:11434 |
| `STORAGE_API_URL` | Storage endpoint | http://storage-service:8001/save |
| `REDIS_URL` | Redis connection | redis://redis:6379 |
| `CACHE_TTL` | Cache TTL (seconds) | 3600 |

### Storage Service

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection | mongodb://mongo:27017 |
| `DB_NAME` | Database name | ollama |

## Docker Services

| Service | Container Name | Port |
|---------|----------------|------|
| FastAPI Gateway | ollama-api | 8000 |
| Storage Service | storage-api | 8001 |
| MongoDB | mongodb | 27017 |
| Redis | redis | 6379 |
| RedisInsight | redis-ui | 8002 |

## Conversation Limits

- **Max messages per conversation**: 100
- **Context window**: Last 10 messages sent to LLM
- **Cache TTL**: 1 hour

---

## Troubleshooting

### Ollama Connection Issues

If FastAPI can't connect to Ollama:
1. Ensure Ollama is running on your host: `ollama serve`
2. Verify Ollama is accessible: `curl http://localhost:11434/api/tags`
3. Check that the `OLLAMA_HOST` env variable is correctly set

### Redis/MongoDB Issues

Check container logs:
```bash
docker-compose logs redis
docker-compose logs mongo
```

### Container Network Issues

Restart all containers:
```bash
docker-compose down
docker-compose up --build
```

## Author

Yanioconjota
