# FastAPI Development Patterns

## Endpoint Organization

**Default**: Group related endpoints in the main file for small services, use routers for services with 10+ endpoints.

```python
# ✅ Good: Small service, endpoints in main.py
@app.post("/conversations")
async def create_conversation(): ...

@app.get("/conversations/{id}")
async def get_conversation(id: str): ...

# ✅ Good: Large service, use routers
from app.routes import conversations, messages
app.include_router(conversations.router, tags=["conversations"])
app.include_router(messages.router, tags=["messages"])
```

**Rationale**:
1. Small services stay simple and readable
2. Large services get organized without premature abstraction
3. Tags enable automatic OpenAPI grouping

## Pydantic Models

**Default**: Define all request/response models with Pydantic. Use `Field()` for defaults and validation.

```python
# ✅ Good: Explicit types, defaults, documentation
class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    model: str = Field(default="llama3")

# ❌ Bad: Using dict or Any
async def create(data: dict): ...  # No validation
```

**One-liner**: "Pydantic models are your first line of defense—invalid data never reaches your logic."

## Error Handling

**Default**: Use HTTPException with specific status codes and clear messages.

```python
# ✅ Good: Specific, actionable errors
if not conversation:
    raise HTTPException(status_code=404, detail="Conversation not found")

if message_count >= MAX_MESSAGES:
    raise HTTPException(status_code=400, detail=f"Message limit ({MAX_MESSAGES}) reached")

# ❌ Bad: Generic errors
raise HTTPException(status_code=500, detail="Error")  # Unhelpful
```

## Async Best Practices

**Default**: Use `async/await` for I/O operations. Use `httpx.AsyncClient` for HTTP calls.

```python
# ✅ Good: Async HTTP client with timeout
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(url, json=payload)

# ❌ Bad: Blocking requests library in async code
import requests
response = requests.post(url)  # Blocks the event loop
```

**Analogy**: "Blocking calls in async code are like a single-lane bridge in a highway—everything stops."

## Dependency Injection

**Default**: Use FastAPI's `Depends()` for shared logic like database connections, auth, etc.

```python
# Define dependency
async def get_db():
    db = await connect_db()
    try:
        yield db
    finally:
        await db.close()

# Use in endpoint
@app.get("/items")
async def get_items(db = Depends(get_db)):
    return await db.items.find().to_list()
```
