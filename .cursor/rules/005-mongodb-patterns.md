# MongoDB Patterns

## Document Design

**Default**: Use UUIDs as document `id` field, keep MongoDB's `_id` for internal use.

```python
from uuid import uuid4

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Rationale**:
1. UUIDs are URL-safe and can be generated client-side
2. `_id` (ObjectId) is preserved for MongoDB internal operations
3. Consistent `id` field across all documents simplifies API design

## Index Strategy

**Default**: Create indexes on startup for commonly queried fields.

```python
def ensure_indexes():
    """Create indexes for optimal query performance."""
    # Sort by most recent
    conversations_collection.create_index(
        [("updated_at", DESCENDING)]
    )
    # Unique constraint on id
    conversations_collection.create_index(
        [("id", ASCENDING)], 
        unique=True
    )
    # Composite index for message queries
    messages_collection.create_index(
        [("conversation_id", ASCENDING), ("timestamp", ASCENDING)]
    )
```

**One-liner**: "An index is like a book's table of contents—without it, every query is a full read."

## Query Patterns

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMMON QUERY PATTERNS                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Find by ID (O(1) with index)                                    │
│  └── collection.find_one({"id": id})                             │
│                                                                  │
│  List with pagination                                            │
│  └── collection.find()                                           │
│        .sort("updated_at", -1)                                   │
│        .skip(offset)                                             │
│        .limit(limit)                                             │
│                                                                  │
│  Count for pagination metadata                                   │
│  └── collection.count_documents({})                              │
│                                                                  │
│  Messages by conversation (sorted)                               │
│  └── messages.find({"conversation_id": id})                      │
│        .sort("timestamp", 1)                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Atomic Updates

**Default**: Use `$set` for partial updates, `$inc` for counters.

```python
# ✅ Good: Atomic update
await conversations.update_one(
    {"id": conversation_id},
    {
        "$set": {"updated_at": datetime.utcnow()},
        "$inc": {"message_count": 1}
    }
)

# ❌ Bad: Read-modify-write (race condition risk)
conv = await conversations.find_one({"id": id})
conv["message_count"] += 1
await conversations.replace_one({"id": id}, conv)
```

## Deletion Strategies

**Default**: Use hard delete for simplicity unless audit trail is required.

```python
# Hard delete (simple, use by default)
async def delete_conversation(id: str):
    await messages.delete_many({"conversation_id": id})
    result = await conversations.delete_one({"id": id})
    return result.deleted_count > 0

# Soft delete (when audit trail needed)
async def soft_delete_conversation(id: str):
    await conversations.update_one(
        {"id": id},
        {"$set": {"deleted_at": datetime.utcnow()}}
    )
```

**Exception**: Use soft delete when:
- Legal/compliance requires audit trails
- Users expect "trash" / "undo" functionality
- Data is needed for analytics even after user deletion
