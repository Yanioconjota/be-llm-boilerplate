# Frontend Integration Rules

## TypeScript Interfaces

**Default**: Backend provides TypeScript interfaces in documentation. Frontend MUST use them as-is.

```typescript
// ✅ Good: Use exact interface from backend docs
export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  cached?: boolean;
}

// ❌ Bad: Inventing your own interface
interface MyMessage {
  msgId: number;        // Wrong type, wrong name
  text: string;         // Wrong name
  isFromBot: boolean;   // Different modeling
}
```

**One-liner**: "The API contract is a promise—break it, and both sides suffer."

## HTTP Client Configuration

**Default**: Use a centralized HTTP client with base URL, interceptors, and error handling.

### Angular

```typescript
// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      withInterceptors([
        errorInterceptor,
        loadingInterceptor
      ])
    )
  ]
};

// api.service.ts
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;
  
  get<T>(path: string) {
    return this.http.get<T>(`${this.baseUrl}${path}`);
  }
}
```

### React

```typescript
// api.ts
const API_BASE = import.meta.env.VITE_API_URL;

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new ApiError(response.status, error.detail);
  }
  
  return response.json();
}
```

## SSE Consumption Pattern

**Default**: Wrap SSE consumption in a service/hook with proper cleanup.

```
┌──────────────────────────────────────────────────────────────────┐
│                    SSE CLIENT LIFECYCLE                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Create AbortController                                       │
│     "Enables cancellation from UI"                               │
│                                                                  │
│  2. Start fetch with signal                                      │
│     "Links request to controller"                                │
│                                                                  │
│  3. Read stream chunks                                           │
│     "Parse SSE format: 'data: {...}'"                            │
│                                                                  │
│  4. Update UI progressively                                      │
│     "Show tokens as they arrive"                                 │
│                                                                  │
│  5. Handle done/error events                                     │
│     "Clean up, show final state"                                 │
│                                                                  │
│  6. Cleanup on unmount                                           │
│     "Call abort() to prevent leaks"                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## State Management for Conversations

**Default**: 
- Use NgRx Signal Store (Angular) or React Context + useReducer (React)
- Store conversation list and active conversation separately
- Optimistically update UI, rollback on error

```typescript
// Angular Signal Store example
export const ChatStore = signalStore(
  { providedIn: 'root' },
  withState<ChatState>({
    conversations: [],
    activeConversation: null,
    messages: [],
    isStreaming: false,
    error: null
  }),
  withMethods((store) => ({
    // Optimistic update
    sendMessage(content: string) {
      const tempMessage: Message = {
        id: `temp-${Date.now()}`,
        content,
        role: 'user',
        // ...
      };
      patchState(store, { 
        messages: [...store.messages(), tempMessage] 
      });
      // Then make API call...
    }
  }))
);
```

**Analogy**: "Optimistic updates are like a waiter who writes your order immediately—corrects later if kitchen says no."

## Error Display Guidelines

| Error Type | User Message | Technical Action |
|------------|--------------|------------------|
| Network error | "Connection lost. Retrying..." | Exponential backoff retry |
| 404 | "Conversation not found" | Redirect to conversation list |
| 400 | Show `detail` from API | Highlight invalid field |
| 500 | "Something went wrong" | Log full error, show generic message |
| SSE error | "Response interrupted" | Show partial content + retry option |
