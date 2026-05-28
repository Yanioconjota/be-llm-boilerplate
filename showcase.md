# Project Knowledge System Showcase

> **The best code isn't written by a senior—it's code any developer can write because decisions are already documented.**

---

## The Problem It Solves

### The Knowledge Loss Cycle

Every engineering team experiences this:

```
┌──────────────────────────────────────────────────────────────────┐
│                    THE KNOWLEDGE LOSS CYCLE                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Senior Developer                                               │
│        │                                                         │
│        ▼                                                         │
│   Makes architectural decision ──────┐                           │
│        │                             │                           │
│        ▼                             │  "Why did we do           │
│   Implements solution                │   it this way?"           │
│        │                             │        ▲                  │
│        ▼                             │        │                  │
│   Leaves company ◄───────────────────┴────────┘                  │
│        │                                                         │
│        ▼                                                         │
│   New developer joins                                            │
│        │                                                         │
│        ▼                                                         │
│   Reinvents wheel / Makes same mistakes                          │
│                                                                  │
│   ════════════════════════════════════════════                   │
│   Repeat every 18-24 months                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Real-world analogy**: It's like a restaurant where the head chef leaves, and the new cook has the recipe but not the "pinch of this, splash of that" knowledge that made the dish special.

### What Gets Lost

| Lost Knowledge | Consequence |
|----------------|-------------|
| "Why we chose SSE over WebSocket" | New dev wastes a week implementing WebSocket |
| "How to properly test SSE endpoints" | Tests are brittle, break randomly |
| "When to break the no-any rule" | Either dogmatic refusal or type-safety holes |
| "What index strategy we use" | Slow queries nobody can explain |

---

## The Solution: Codified Knowledge + AI Delivery

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SYSTEM STRUCTURE                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  .cursor/                                                        │
│  ├── rules/          → HOW we do things here                     │
│  │   ├── 001-*.md       (conventions, patterns, decisions)       │
│  │   ├── 002-*.md                                                │
│  │   └── ...                                                     │
│  │                                                               │
│  ├── commands/       → WHAT we can automate                      │
│  │   └── new-*.md       (scaffolding, generation)                │
│  │                                                               │
│  └── skills/         → HOW to debug/investigate                  │
│      └── debug-*.md     (diagnostic workflows)                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Real-world analogy**: 
- **Rules** are like a kitchen's recipe book—not just ingredients, but techniques and why they matter
- **Commands** are like prep stations—mise en place, ready to go
- **Skills** are like troubleshooting guides—"if the sauce breaks, here's how to fix it"

### Rules vs Commands vs Skills

| Aspect | Rules | Commands | Skills |
|--------|-------|----------|--------|
| **Purpose** | Document decisions | Automate creation | Guide investigation |
| **When used** | During development | At task start | When stuck |
| **Format** | Principles + examples | Step-by-step workflow | Diagnostic flowchart |
| **Updates** | When patterns change | When scaffolds improve | When new issues found |
| **Example** | "Use SSE for streaming" | "Create new endpoint" | "Debug SSE issues" |

---

## Featured Rules with Reasoning

### Rule 1: SSE Over WebSocket for LLM Streaming

**One-liner**: "SSE is HTTP that learned to talk continuously—simple, reliable, and perfect for LLM streaming."

**Default Behavior**:
Use Server-Sent Events (SSE) for streaming LLM responses from backend to client.

**Rationale**:
1. **Simpler protocol**: SSE is built on HTTP/1.1, works through all proxies and firewalls
2. **Automatic reconnection**: Browsers handle reconnection natively
3. **One-way is enough**: LLM streaming only needs server→client, not bidirectional
4. **Interview-relevant**: SSE is commonly asked about in frontend interviews

```
┌──────────────────────────────────────────────────────────────────┐
│                    CHOOSE YOUR PROTOCOL                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REST (POST/GET)                                                 │
│  └── Request → Response → Done                                   │
│      Use for: CRUD operations, short requests                    │
│                                                                  │
│  SSE (Server-Sent Events)                                        │
│  └── Request → Stream → Stream → Stream → Done                   │
│      Use for: LLM responses, notifications, progress             │
│                                                                  │
│  WebSocket                                                       │
│  └── ←→ Bidirectional continuous ←→                              │
│      Use for: Chat rooms, gaming, collaboration                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Documented Exceptions**:
- Use WebSocket when users can send messages while receiving (true chat rooms)
- Use WebSocket when you need server-initiated messages without prior request

**Anti-Patterns**:
```python
# ❌ Bad: Polling for LLM response
while not response.complete:
    await asyncio.sleep(0.5)
    status = await check_status()

# ✅ Good: Streaming via SSE
async for token in stream_from_llm():
    yield {"data": json.dumps({"chunk": token})}
```

---

### Rule 2: Cache Failures Should Never Break the App

**One-liner**: "A broken cache is an inconvenience; a broken app is a disaster."

**Default Behavior**:
Wrap all cache operations in try/except. Log failures, return graceful fallback.

**Rationale**:
1. **Availability over performance**: Users prefer slow over broken
2. **Redis restarts**: During deployments or maintenance, cache is temporarily unavailable
3. **Network hiccups**: Transient failures are common in containerized environments

```python
# ✅ Good: Graceful degradation
def get_cached_response(prompt: str) -> Optional[str]:
    try:
        cached = redis_client.get(build_key(prompt))
        if cached:
            logging.info(f"Cache HIT")
            return cached.decode('utf-8')
        logging.info(f"Cache MISS")
        return None
    except redis.RedisError as e:
        logging.warning(f"Cache error (degraded mode): {e}")
        return None  # Proceed without cache

# ❌ Bad: Let cache errors crash the request
def get_cached_response(prompt: str) -> str:
    return redis_client.get(build_key(prompt)).decode('utf-8')  # Raises if Redis down
```

**Real-world analogy**: It's like a restaurant that can still serve food even if the reservation system is down—write names on paper and keep going.

---

### Rule 3: Test Behavior, Not Implementation

**One-liner**: "Test WHAT the code does, not HOW it does it."

**Default Behavior**:
Write tests that verify API contracts and user-facing behavior, not internal function calls.

**Rationale**:
1. **Refactor-friendly**: Internal changes shouldn't break tests
2. **Meaningful failures**: Test failures indicate real bugs, not style changes
3. **Documentation**: Tests become usage examples

```typescript
// ❌ Bad: Testing implementation
it('should call patchState with isLoading true', () => {
  const spy = spyOn(store, 'patchState');
  store.sendMessage('Hello');
  expect(spy).toHaveBeenCalledWith({ isLoading: true });
});

// ✅ Good: Testing behavior
it('should show loading state while sending', () => {
  store.sendMessage('Hello');
  expect(store.isLoading()).toBe(true);
});

// ✅ Good: Testing user interaction
it('should send message when form submitted', () => {
  const input = getByRole('textbox');
  const button = getByRole('button', { name: /send/i });
  
  fireEvent.change(input, { target: { value: 'Hello' } });
  fireEvent.click(button);
  
  expect(mockApi.sendMessage).toHaveBeenCalledWith('Hello');
});
```

**Documented Exceptions**:
- Test internal helpers when they have complex logic with many edge cases
- Test caching logic directly when TTL and key generation are critical

---

### Rule 4: Pydantic Models as First Line of Defense

**One-liner**: "Pydantic models are your first line of defense—invalid data never reaches your logic."

**Default Behavior**:
Define explicit Pydantic models for ALL request and response bodies.

**Rationale**:
1. **Automatic validation**: Invalid requests rejected before hitting your code
2. **Self-documenting API**: OpenAPI/Swagger generated automatically
3. **Type safety**: IDE autocomplete, editor warnings
4. **Serialization handled**: JSON encoding/decoding just works

```python
# ✅ Good: Explicit, validated, documented
class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    model: str = Field(default="llama3")

@app.post("/conversations", response_model=Conversation)
async def create(request: ConversationCreate):
    # request is already validated
    return await save_conversation(request)

# ❌ Bad: No validation, no documentation
@app.post("/conversations")
async def create(data: dict):  # What fields? What types? Who knows!
    title = data.get("title")  # KeyError? None? String? Anything!
    return await save_conversation(data)
```

**Real-world analogy**: It's like airport security—check bags before they get on the plane, not mid-flight.

---

### Rule 5: Optimistic Updates with Rollback

**One-liner**: "Like a waiter who writes your order immediately—corrects later if kitchen says no."

**Default Behavior**:
Update UI immediately on user action, revert if server returns error.

**Rationale**:
1. **Perceived performance**: App feels instant even with network latency
2. **User confidence**: Immediate feedback confirms action was received
3. **Reality**: Most operations succeed; optimize for the common case

```
┌──────────────────────────────────────────────────────────────────┐
│                    OPTIMISTIC UPDATE FLOW                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User clicks "Send"                                           │
│     └── Message appears immediately in UI (optimistic)           │
│                                                                  │
│  2. API request fires                                            │
│     └── User sees their message, can keep typing                 │
│                                                                  │
│  3a. Success (99% of cases)                                      │
│      └── Update message with server ID, timestamp                │
│                                                                  │
│  3b. Failure (rare)                                              │
│      └── Remove message, show error, restore input               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```typescript
// Implementation pattern
sendMessage(content: string) {
  // 1. Optimistic: Add to UI immediately
  const tempId = `temp-${Date.now()}`;
  const tempMessage = { id: tempId, content, role: 'user' };
  this.messages.update(msgs => [...msgs, tempMessage]);
  
  // 2. Fire API request
  this.api.sendMessage(content).pipe(
    tap(serverMessage => {
      // 3a. Success: Replace temp with real message
      this.messages.update(msgs => 
        msgs.map(m => m.id === tempId ? serverMessage : m)
      );
    }),
    catchError(error => {
      // 3b. Failure: Remove temp message, show error
      this.messages.update(msgs => 
        msgs.filter(m => m.id !== tempId)
      );
      this.error.set(error.message);
      return EMPTY;
    })
  ).subscribe();
}
```

---

## Commands: Automation at Your Fingertips

### Command: `new-endpoint`

**Purpose**: Scaffold a new API endpoint with models, route, and tests.

```
┌──────────────────────────────────────────────────────────────────┐
│                    new-endpoint WORKFLOW                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input:                                                          │
│  new-endpoint fast-api POST /conversations/{id}/archive          │
│                                                                  │
│  Generated:                                                      │
│  ├── Pydantic ArchiveRequest model                               │
│  ├── Pydantic ArchiveResponse model                              │
│  ├── Endpoint function with error handling                       │
│  ├── OpenAPI summary and tags                                    │
│  └── Test stubs (happy path + error case)                        │
│                                                                  │
│  Time saved: ~30 minutes of boilerplate                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Real-world analogy**: Like a prep cook who has all the ingredients measured and ready—you just add the secret sauce (business logic).

---

## Skills: Diagnostic Expertise on Demand

### Skill: Debug SSE Streaming Issues

**Purpose**: Systematic approach to diagnosing SSE problems.

```
┌──────────────────────────────────────────────────────────────────┐
│                    SSE DEBUG DECISION TREE                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  "Stream shows no content"                                       │
│        │                                                         │
│        ▼                                                         │
│  Does curl show events? ─── No ──► Check backend logs            │
│        │                          Check Ollama running           │
│       Yes                                                        │
│        │                                                         │
│        ▼                                                         │
│  Is JSON valid? ─── No ──► Check SSE format                      │
│        │                   (event:\ndata:\n\n)                   │
│       Yes                                                        │
│        │                                                         │
│        ▼                                                         │
│  Check browser console ──► Look for parse errors                 │
│        │                   Check element references              │
│        ▼                                                         │
│  Fixed!                                                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Quick diagnostic commands included**:
```bash
# Test backend directly
curl -N -X POST http://localhost:8000/conversations/ID/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Check service logs
docker logs ollama-api --tail 50

# Verify cache state
docker exec redis redis-cli KEYS "ollama:*"
```

---

## Value Proposition by Audience

### For New Developers

| Aspect | Without System | With System |
|--------|----------------|-------------|
| **Time to first PR** | 2-3 weeks | 3-5 days |
| **"Where do I put this?"** | Ask 5 people, get 6 answers | Read folder structure rule |
| **"How do we test this?"** | Copy random existing test | Follow testing patterns rule |
| **Debugging SSE** | Hours of trial and error | Follow skill flowchart |

**Before**: "I've been here a month and still don't know where models go."

**After**: "Day 2 and I already shipped a feature. The rules explained everything."

### For the Team

| Aspect | Without System | With System |
|--------|----------------|-------------|
| **PR review focus** | 40% style debates | 95% business logic |
| **Onboarding load** | 2 hours/day for a week | 30 min intro, then self-serve |
| **Consistency** | "Depends who wrote it" | "It's all the same" |
| **Bus factor** | 1-2 people | The whole team |

**Before**: "Code reviews take forever because everyone has different opinions."

**After**: "Opinions are documented. Reviews discuss what matters: does it work correctly?"

### For the Project Long-Term

| Aspect | Without System | With System |
|--------|----------------|-------------|
| **After senior leaves** | Panic, archaeology | Read their documented decisions |
| **Technology upgrades** | "Why did we do X?" | Rules explain the why |
| **New similar project** | Start from scratch | Fork rules as foundation |
| **Audit/compliance** | "Uh... let me check" | Point to documented patterns |

**Before**: "Our best developer left and took half the knowledge with them."

**After**: "Their expertise is in the rules. New hires benefit from their thinking."

---

## Design Decisions

### Why Numbered Rule Files?

```
001-project-architecture.md
002-fastapi-patterns.md
003-sse-streaming.md
```

**Decision**: Number prefix for explicit ordering.

**Rationale**:
1. Foundational rules (architecture) come before specific rules (SSE)
2. Easy to insert new rules: `002a-new-rule.md` or renumber
3. Alphabetical sorting in file explorers matches logical order

### Why Markdown over JSON/YAML?

**Decision**: Rules are prose Markdown with embedded code blocks.

**Rationale**:
1. **Human-first**: Rules are read by humans, not parsed by machines
2. **Rich examples**: Code blocks with syntax highlighting
3. **AI-friendly**: LLMs excel at understanding natural language + code
4. **Versionable**: Git diffs are readable

### Why Separate Commands and Skills?

**Decision**: Commands scaffold new things; Skills diagnose existing things.

**Rationale**:
1. **Different triggers**: Commands are proactive; Skills are reactive
2. **Different outputs**: Commands create files; Skills provide diagnostics
3. **Different maintenance**: Commands update with tech; Skills update with issues

---

## Success Metrics

### Quantitative

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Onboarding time | 4 weeks | 1 week | Time to first solo PR |
| PR rejection rate (style) | 40% | <5% | PR comments tagged "style" |
| Debugging time | Hours | Minutes | Time from "bug report" to "root cause" |
| Documentation searches | 10+/week | 2-3/week | "Where is X?" Slack messages |

### Qualitative

- **New developers say**: "I knew exactly where to look"
- **Reviewers say**: "I can focus on logic, not formatting"
- **Future maintainers say**: "I understand why this was built this way"

---

## Conclusion: The 2-Minute Pitch

### The Problem

Engineering teams lose knowledge constantly. Decisions made by developers who leave become archaeological mysteries. New team members reinvent wheels. Code reviews become style debates. Every team rotation restarts the learning curve.

### The Solution

A **Project Knowledge System** that captures:
- **Rules**: Documented decisions with rationale and exceptions
- **Commands**: Automated scaffolding for common tasks
- **Skills**: Diagnostic workflows for debugging

### The Delivery

**AI assistance** reads these documents and applies them consistently. The knowledge is always available, never forgets, and explains its reasoning.

### The Value

| Stakeholder | Benefit |
|-------------|---------|
| **New devs** | Productive in days, not weeks |
| **Team** | Reviews focus on logic, not style |
| **Project** | Knowledge survives team changes |

### The One-Liner

> **"The AI is the delivery mechanism, but the real value is having decisions documented with their reasoning."**

Knowledge should survive team rotation. This system ensures it does.

---

## Quick Reference: This Project's Rules

| # | Rule | One-Liner |
|---|------|-----------|
| 001 | Project Architecture | "Services are containers; environment is templated" |
| 002 | FastAPI Patterns | "Pydantic is your first line of defense" |
| 003 | SSE Streaming | "SSE is HTTP that learned to talk continuously" |
| 004 | Caching Patterns | "A broken cache is an inconvenience; a broken app is a disaster" |
| 005 | MongoDB Patterns | "An index is like a book's table of contents" |
| 006 | Frontend Integration | "The API contract is a promise—break it, both sides suffer" |
| 007 | Testing Patterns | "Test WHAT the code does, not HOW it does it" |

---

*This showcase was generated from the `.cursor/rules/`, `.cursor/commands/`, and `.cursor/skills/` folders of the be-llm-boilerplate project.*
