# Server-Sent Events (SSE) Streaming Rules

## When to Use SSE vs WebSocket vs REST

```
┌──────────────────────────────────────────────────────────────────┐
│                    CHOOSE YOUR PROTOCOL                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REST (POST/GET)                                                 │
│  └── Request → Response → Done                                   │
│      Use for: CRUD, short operations                             │
│                                                                  │
│  SSE (Server-Sent Events)                                        │
│  └── Request → Stream → Stream → Done                            │
│      Use for: LLM streaming, progress updates, notifications     │
│                                                                  │
│  WebSocket                                                       │
│  └── ←→ Bidirectional messages ←→                                │
│      Use for: Chat rooms, real-time collaboration, gaming        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**One-liner**: "SSE is HTTP that learned to talk continuously—simple, reliable, and perfect for LLM streaming."

## SSE Event Format

**Default**: Use JSON events with consistent structure:

```python
# Standard event structure
yield {
    "event": "message",
    "data": json.dumps({
        "chunk": "token text",
        "done": False,
        "cached": False
    })
}

# Error events
yield {
    "event": "error",
    "data": json.dumps({
        "error": "llm_unavailable",
        "message": "Cannot connect to Ollama"
    })
}

# Completion event
yield {
    "event": "message",
    "data": json.dumps({
        "chunk": "",
        "done": True,
        "cached": was_cached
    })
}
```

**Rationale**:
1. `event` field enables client-side event filtering
2. `done` flag signals stream completion
3. `cached` indicates if response came from cache (useful for debugging)

## Error Handling in Streams

**Default**: Catch errors inside the generator and yield error events instead of raising exceptions.

```python
async def event_generator():
    try:
        async for token in stream_from_llm():
            yield {"data": json.dumps({"chunk": token})}
    except httpx.ConnectError:
        yield {
            "event": "error",
            "data": json.dumps({
                "error": "llm_unavailable",
                "message": "LLM service is not responding"
            })
        }
        return  # End the stream gracefully
```

**Anti-Pattern**:
```python
# ❌ Bad: Exception breaks the stream without informing client
async def event_generator():
    async for token in stream_from_llm():  # If this fails, client gets nothing
        yield {"data": json.dumps({"chunk": token})}
```

## Client Implementation Guidelines

**Default**: Use `fetch()` with streaming reader, not `EventSource` (for POST requests).

```typescript
// ✅ Good: fetch with streaming for POST requests
const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
    signal: abortController.signal  // Enable cancellation
});

const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Process chunks
}

// ❌ Bad: EventSource only works with GET
const eventSource = new EventSource(url);  // Cannot send POST body
```

## Caching Strategy for Streams

**Default**: Cache completed responses, stream from cache word-by-word for consistent UX.

```python
# Check cache before streaming
cached_response = get_cached_response(prompt)

if cached_response:
    # Stream cached response with artificial delay for smooth UX
    for word in cached_response.split(" "):
        yield {"data": json.dumps({"chunk": word + " ", "cached": True})}
        await asyncio.sleep(0.02)
else:
    # Stream from LLM and cache the complete response
    full_response = ""
    async for token in stream_from_llm(prompt):
        full_response += token
        yield {"data": json.dumps({"chunk": token, "cached": False})}
    
    cache_response(prompt, full_response)
```

**Analogy**: "Like a waiter who remembers your usual order—delivers it smoothly while still going through the motions."
