# Command: Create New Endpoint

**Trigger**: `new-endpoint <service> <method> <path> <description>`

## What This Command Does

Creates a new API endpoint following project conventions:
1. Adds route to the appropriate service
2. Creates Pydantic request/response models
3. Adds error handling
4. Updates OpenAPI tags
5. Suggests test cases

## Execution Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    NEW ENDPOINT WORKFLOW                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Parse command arguments                                      │
│     service: fast-api | storage-service                          │
│     method: GET | POST | PUT | DELETE                            │
│     path: /conversations/{id}/archive                            │
│                                                                  │
│  2. Generate Pydantic models                                     │
│     - Request body model (if POST/PUT)                           │
│     - Response model                                             │
│                                                                  │
│  3. Create endpoint function                                     │
│     - Async function with type hints                             │
│     - HTTPException error handling                               │
│     - OpenAPI summary and description                            │
│                                                                  │
│  4. Add to appropriate file                                      │
│     - main.py (small service)                                    │
│     - routes/<feature>.py (large service)                        │
│                                                                  │
│  5. Generate test stub                                           │
│     - Happy path test                                            │
│     - Error case test                                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Example Usage

```bash
new-endpoint fast-api POST /conversations/{id}/archive "Archive a conversation"
```

## Generated Code Template

```python
# Models (added to models.py)
class ArchiveRequest(BaseModel):
    """Request body for archiving a conversation."""
    reason: Optional[str] = Field(default=None, max_length=500)

class ArchiveResponse(BaseModel):
    """Response after archiving."""
    success: bool
    archived_at: datetime

# Endpoint (added to main.py or routes/conversations.py)
@app.post(
    "/conversations/{conversation_id}/archive",
    response_model=ArchiveResponse,
    summary="Archive a conversation",
    tags=["conversations"]
)
async def archive_conversation(
    conversation_id: str,
    request: ArchiveRequest
) -> ArchiveResponse:
    """
    Archive a conversation to remove it from active list.
    
    - **conversation_id**: UUID of the conversation to archive
    - **reason**: Optional reason for archiving
    """
    # Verify conversation exists
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Perform archive logic
    archived_at = datetime.utcnow()
    await conversations_collection.update_one(
        {"id": conversation_id},
        {"$set": {"archived_at": archived_at, "archive_reason": request.reason}}
    )
    
    return ArchiveResponse(success=True, archived_at=archived_at)

# Test stub (added to tests/test_conversations.py)
def test_archive_conversation():
    # Setup: Create a conversation first
    create_response = client.post("/conversations", json={"title": "Test"})
    conv_id = create_response.json()["id"]
    
    # Test: Archive the conversation
    response = client.post(f"/conversations/{conv_id}/archive", json={})
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_archive_nonexistent_conversation():
    response = client.post("/conversations/fake-id/archive", json={})
    assert response.status_code == 404
```

## Checklist After Running

- [ ] Review generated models for correct types
- [ ] Add business logic to endpoint
- [ ] Run tests to verify
- [ ] Update frontend TypeScript interfaces if needed
- [ ] Update API documentation
