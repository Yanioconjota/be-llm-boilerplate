# Microservices Backend with Ollama LLM

A complete FastAPI microservices backend with Redis caching, MongoDB persistence, and Ollama LLM integration.

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

**Flow**:
1. Client sends prompt to FastAPI `/ask`
2. FastAPI checks Redis cache (HIT → return immediately)
3. On MISS → call Ollama LLM → cache response → persist to MongoDB
4. Return response with `{ cached: true/false }` flag

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
    │       └── save.py
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

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/joker` | Demo: get a joke from Ollama |
| POST | `/ask` | Send prompt, get LLM response |

### Storage Service (Port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/save` | Save prompt/response pair |
| GET | `/health` | Check MongoDB connection |

## Usage Examples

```bash
# Test FastAPI health
curl http://localhost:8000/

# Test Storage health
curl http://localhost:8001/health

# Send a prompt (first call = cache miss)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'

# Same prompt again (cache hit, much faster)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'
```

## Response Format

```json
{
  "response": "The sky appears blue because...",
  "cached": false
}
```

- `cached: true` → Response from Redis (fast)
- `cached: false` → Fresh from Ollama (slower, now cached)

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
| `COLLECTION_NAME` | Collection name | responses |

## Docker Services

| Service | Container Name | Port |
|---------|----------------|------|
| FastAPI Gateway | ollama-api | 8000 |
| Storage Service | storage-api | 8001 |
| MongoDB | mongodb | 27017 |
| Redis | redis | 6379 |
| RedisInsight | redis-ui | 8002 |

## Development

To run with hot-reload enabled (default in development):

```bash
docker-compose up --build
```

The FastAPI service mounts the local directory as a volume, so changes to Python files will automatically reload the server.

---

## Frontend Integration

The backend has CORS enabled (`allow_origins=["*"]`), so frontend apps running on `localhost:4200` (Angular) or `localhost:5173` (React/Vite) will work without issues.

### TypeScript Interfaces

Create these interfaces to type your API requests and responses:

```typescript
// models/llm.models.ts

export interface PromptRequest {
  prompt: string;
}

export interface LlmResponse {
  response: string;
  cached: boolean;
}

export interface HealthCheckResponse {
  app_name: string;
  env: string;
  host: string;
  port: string;
  message: string;
}

export interface JokeResponse {
  result: string;
}
```

### API Reference

| Endpoint | Method | Request Body | Response Type |
|----------|--------|--------------|---------------|
| `/` | GET | - | `HealthCheckResponse` |
| `/ask` | POST | `{ prompt: string }` | `{ response: string, cached: boolean }` |
| `/joker` | GET | - | `{ result: string }` |

---

## Angular Integration

### App Configuration

```typescript
// app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([]))
  ]
};
```

### LLM Service

```typescript
// services/llm.service.ts
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import { PromptRequest, LlmResponse, HealthCheckResponse, JokeResponse } from '../models/llm.models';

@Injectable({ providedIn: 'root' })
export class LlmService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://localhost:8000';

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly lastResponse = signal<LlmResponse | null>(null);

  askPrompt(prompt: string): Observable<LlmResponse> {
    this.loading.set(true);
    this.error.set(null);
    
    const request: PromptRequest = { prompt };
    
    return this.http.post<LlmResponse>(`${this.baseUrl}/ask`, request).pipe(
      tap((response) => {
        this.lastResponse.set(response);
        this.loading.set(false);
      }),
      catchError((err) => {
        this.error.set(err.message || 'An error occurred');
        this.loading.set(false);
        throw err;
      })
    );
  }

  healthCheck(): Observable<HealthCheckResponse> {
    return this.http.get<HealthCheckResponse>(this.baseUrl);
  }

  getJoke(): Observable<JokeResponse> {
    return this.http.get<JokeResponse>(`${this.baseUrl}/joker`);
  }
}
```

### Example Component

```typescript
// components/chat.component.ts
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LlmService } from '../services/llm.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="chat-container">
      <h2>Ollama Chat</h2>
      
      <textarea 
        [(ngModel)]="prompt" 
        placeholder="Enter your prompt..."
        rows="4"
      ></textarea>
      
      <button (click)="sendPrompt()" [disabled]="llmService.loading()">
        @if (llmService.loading()) {
          Thinking...
        } @else {
          Send
        }
      </button>

      @if (llmService.error(); as error) {
        <div class="error">{{ error }}</div>
      }

      @if (llmService.lastResponse(); as response) {
        <div class="response">
          <p>{{ response.response }}</p>
          <small class="cache-indicator">
            @if (response.cached) {
              ⚡ From cache
            } @else {
              🔄 Fresh response
            }
          </small>
        </div>
      }
    </div>
  `
})
export class ChatComponent {
  protected readonly llmService = inject(LlmService);
  protected prompt = '';

  sendPrompt(): void {
    if (!this.prompt.trim()) return;

    this.llmService.askPrompt(this.prompt).subscribe({
      next: () => console.log('Response received'),
      error: (err) => console.error('Error:', err)
    });
  }
}
```

---

## React + TypeScript Integration

### API Client

```typescript
// api/llm-api.ts
import { PromptRequest, LlmResponse, HealthCheckResponse, JokeResponse } from '../models/llm.models';

const BASE_URL = 'http://localhost:8000';

export const llmApi = {
  async askPrompt(prompt: string): Promise<LlmResponse> {
    const request: PromptRequest = { prompt };
    
    const response = await fetch(`${BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await fetch(BASE_URL);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async getJoke(): Promise<JokeResponse> {
    const response = await fetch(`${BASE_URL}/joker`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },
};
```

### Custom Hook

```typescript
// hooks/useLlm.ts
import { useState, useCallback } from 'react';
import { llmApi } from '../api/llm-api';
import { LlmResponse } from '../models/llm.models';

interface UseLlmReturn {
  response: LlmResponse | null;
  loading: boolean;
  error: string | null;
  askPrompt: (prompt: string) => Promise<void>;
  clearResponse: () => void;
}

export function useLlm(): UseLlmReturn {
  const [response, setResponse] = useState<LlmResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const askPrompt = useCallback(async (prompt: string) => {
    setLoading(true);
    setError(null);

    try {
      const result = await llmApi.askPrompt(prompt);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResponse = useCallback(() => {
    setResponse(null);
    setError(null);
  }, []);

  return { response, loading, error, askPrompt, clearResponse };
}
```

### Example Component

```tsx
// components/Chat.tsx
import { useState, FormEvent } from 'react';
import { useLlm } from '../hooks/useLlm';

export function Chat() {
  const [prompt, setPrompt] = useState('');
  const { response, loading, error, askPrompt } = useLlm();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    await askPrompt(prompt);
  };

  return (
    <div className="chat-container">
      <h2>Ollama Chat</h2>

      <form onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt..."
          rows={4}
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Thinking...' : 'Send'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {response && (
        <div className="response">
          <p>{response.response}</p>
          <small className="cache-indicator">
            {response.cached ? '⚡ From cache' : '🔄 Fresh response'}
          </small>
        </div>
      )}
    </div>
  );
}
```

### Alternative: Using React Query (TanStack Query)

```typescript
// hooks/useLlmQuery.ts
import { useMutation } from '@tanstack/react-query';
import { llmApi } from '../api/llm-api';

export function useAskPrompt() {
  return useMutation({
    mutationFn: (prompt: string) => llmApi.askPrompt(prompt),
  });
}

// Usage in component:
// const { mutate: askPrompt, data: response, isPending, error } = useAskPrompt();
```

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
