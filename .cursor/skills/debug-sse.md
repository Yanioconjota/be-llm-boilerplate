# Skill: Debug SSE Streaming Issues

## When to Use This Skill

Use when:
- SSE stream starts but shows no content
- Chunks appear but final message is incomplete
- Frontend shows empty responses despite backend logs showing success
- "Connection closed" errors during streaming

## Diagnostic Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    SSE DEBUG WORKFLOW                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Verify backend is streaming                                  │
│     curl -N -X POST http://localhost:8000/conversations/ID/stream│
│     -H "Content-Type: application/json"                          │
│     -d '{"prompt": "Hello"}'                                     │
│                                                                  │
│  2. Check SSE event format                                       │
│     Expected: "event: message\ndata: {...}\n\n"                  │
│     Common issue: Missing double newline between events          │
│                                                                  │
│  3. Verify JSON parsing                                          │
│     Open browser DevTools → Console                              │
│     Look for "SSE parse error" logs                              │
│                                                                  │
│  4. Check for CORS issues                                        │
│     Network tab → Look for blocked requests                      │
│     Backend must allow streaming origin                          │
│                                                                  │
│  5. Verify AbortController cleanup                               │
│     Memory leaks = orphaned streams                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Common Issues and Fixes

### Issue 1: Empty Response in UI

**Symptoms**: Backend logs show "Response completed (X chars)" but UI shows nothing.

**Diagnosis**:
```bash
# Check what backend is actually sending
curl -N -X POST http://localhost:8000/conversations/YOUR_ID/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' 2>&1 | head -20
```

**Expected output**:
```
event: message
data: {"chunk": "Hello", "done": false, "cached": false}

event: message
data: {"chunk": " world", "done": false, "cached": false}
```

**Common fixes**:
1. Frontend parsing wrong line format (check `line.startsWith('data: ')`)
2. Event lines being skipped (add `if (line.startsWith('event:')) continue;`)
3. Element references lost (use unique IDs per message)

### Issue 2: Partial Response

**Symptoms**: Response cuts off mid-sentence.

**Diagnosis**:
```python
# Add logging to backend
async def event_generator():
    # ...
    finally:
        logging.info(f"Stream ended. Total chars: {len(full_response)}")
```

**Common fixes**:
1. Client disconnecting early (check AbortController)
2. Timeout on httpx client (increase `timeout` parameter)
3. Ollama connection drop (check Ollama logs)

### Issue 3: Duplicate Messages

**Symptoms**: Same message appears multiple times.

**Diagnosis**:
```javascript
// Add to frontend SSE parsing
console.log('Processing line:', line);
console.log('Current fullResponse length:', fullResponse.length);
```

**Common fixes**:
1. Multiple event listeners attached (use unique IDs)
2. React strict mode double-rendering (check for duplicate fetch calls)
3. Page reload not clearing state

## Quick Diagnostic Commands

```bash
# Test backend health
curl http://localhost:8000/

# Test conversation creation
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Debug Test"}'

# Test SSE stream (keep connection open with -N)
curl -N -X POST http://localhost:8000/conversations/CONV_ID/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello"}'

# Check Docker logs
docker logs ollama-api --tail 50
docker logs storage-api --tail 50

# Check Redis cache
docker exec redis redis-cli KEYS "ollama:*"

# Check MongoDB messages
docker exec mongodb mongosh ollama --eval "db.messages.find().limit(5)"
```

## Frontend Debug Checklist

```javascript
// Add these console logs to SSE handler:

// 1. Before fetch
console.log('Starting SSE request', { conversationId, prompt });

// 2. On each chunk
console.log('SSE event:', event);

// 3. On stream end
console.log('Stream complete', { fullResponse, chunkCount, cached });

// 4. On error
console.error('SSE error:', error);
```

## Resolution Verification

After fixing, verify:
1. [ ] Fresh conversation works end-to-end
2. [ ] Cached response works (same prompt twice)
3. [ ] Error handling works (stop Ollama, test error event)
4. [ ] Cancel button works (abort mid-stream)
5. [ ] Page reload shows saved messages
