# Testing Patterns

## Backend Testing (pytest)

**Default**: Test endpoints through the FastAPI test client, not implementation details.

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ✅ Good: Test behavior through API
def test_create_conversation():
    response = client.post("/conversations", json={"title": "Test"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test"

# ✅ Good: Test error handling
def test_get_nonexistent_conversation():
    response = client.get("/conversations/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# ❌ Bad: Testing internal functions directly
def test_build_cache_key():  # Implementation detail
    key = build_cache_key("hello", "llama3")
    assert key.startswith("ollama:")
```

**One-liner**: "Test WHAT the API does, not HOW it does it."

## Frontend Testing (Angular/React)

**Default**: Test component behavior from user perspective, mock HTTP calls.

### Angular Component Testing

```typescript
describe('ChatComponent', () => {
  let component: ChatComponent;
  let fixture: ComponentFixture<ChatComponent>;
  let chatService: jasmine.SpyObj<ChatService>;

  beforeEach(async () => {
    chatService = jasmine.createSpyObj('ChatService', ['sendMessage']);
    
    await TestBed.configureTestingModule({
      imports: [ChatComponent],
      providers: [
        { provide: ChatService, useValue: chatService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ChatComponent);
    component = fixture.componentInstance;
  });

  // ✅ Good: Test user interaction
  it('should send message when form submitted', () => {
    const input = fixture.nativeElement.querySelector('textarea');
    const button = fixture.nativeElement.querySelector('button[type="submit"]');
    
    input.value = 'Hello';
    input.dispatchEvent(new Event('input'));
    button.click();
    
    expect(chatService.sendMessage).toHaveBeenCalledWith('Hello');
  });

  // ✅ Good: Test UI state
  it('should show loading indicator while streaming', () => {
    component.isStreaming.set(true);
    fixture.detectChanges();
    
    const loader = fixture.nativeElement.querySelector('.loading');
    expect(loader).toBeTruthy();
  });
});
```

### Store Testing

```typescript
// ✅ Good: Test store behavior, not implementation
describe('ChatStore', () => {
  it('should add message to list when sendMessage called', () => {
    const store = new ChatStore();
    
    store.sendMessage('Hello');
    
    expect(store.messages().length).toBe(1);
    expect(store.messages()[0].content).toBe('Hello');
  });
});

// ❌ Bad: Testing internal state mutations
it('should call patchState with correct args', () => {
  // Testing implementation, not behavior
});
```

## Test Organization

```
┌──────────────────────────────────────────────────────────────────┐
│                    TEST FILE STRUCTURE                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Backend                                                         │
│  ├── tests/                                                      │
│  │   ├── test_conversations.py                                   │
│  │   ├── test_messages.py                                        │
│  │   └── test_streaming.py                                       │
│  └── pytest.ini                                                  │
│                                                                  │
│  Frontend                                                        │
│  ├── src/app/features/chat/                                      │
│  │   ├── chat.component.ts                                       │
│  │   └── chat.component.spec.ts  ← Co-located                    │
│  └── src/app/shared/services/                                    │
│      ├── api.service.ts                                          │
│      └── api.service.spec.ts     ← Co-located                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## What NOT to Test

- Third-party library internals (trust they work)
- CSS styling (use visual regression tools if needed)
- Auto-generated code (Pydantic validation, Angular forms built-in validation)
- Simple getters/setters with no logic

## SSE Testing Strategy

**Default**: Mock SSE responses in frontend tests, test actual streaming in backend integration tests.

```typescript
// Mock SSE for frontend tests
const mockSseResponse = `event: message
data: {"chunk": "Hello", "done": false}

event: message
data: {"chunk": " world", "done": false}

event: message
data: {"chunk": "", "done": true}
`;

// Backend integration test
async def test_sse_streaming():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("POST", "/conversations/123/stream", json={"prompt": "Hi"}) as response:
            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(json.loads(line[6:]))
            
            assert any(c.get("done") for c in chunks)
```
