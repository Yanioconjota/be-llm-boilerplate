# Redis Caching Patterns

## Cache Key Strategy

**Default**: Use prefixed, hashed keys with all relevant parameters.

```python
import hashlib

def build_cache_key(prompt: str, model: str) -> str:
    """Build deterministic cache key from prompt and model."""
    content = f"{prompt}:{model}"
    hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"ollama:{hash_val}"
```

**Rationale**:
1. Prefix (`ollama:`) enables namespace separation and bulk operations
2. Hash prevents key length issues and special character problems
3. Including model ensures different models don't share cached responses

## TTL Guidelines

```
┌──────────────────────────────────────────────────────────────────┐
│                    CACHE TTL RECOMMENDATIONS                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LLM Responses    → 1 hour (3600s)                               │
│  "Balance freshness with compute savings"                        │
│                                                                  │
│  Session Data     → 24 hours (86400s)                            │
│  "User expectations for persistence"                             │
│                                                                  │
│  Rate Limits      → 1 minute (60s)                               │
│  "Short-lived by design"                                         │
│                                                                  │
│  Feature Flags    → 5 minutes (300s)                             │
│  "Quick propagation, reduced DB load"                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Cache Miss Handling

**Default**: Log cache hits and misses for monitoring. Never fail on cache errors.

```python
def get_cached_response(prompt: str, model: str) -> Optional[str]:
    try:
        key = build_cache_key(prompt, model)
        cached = redis_client.get(key)
        
        if cached:
            logging.info(f"Cache HIT for key: {key}")
            return cached.decode('utf-8')
        else:
            logging.info(f"Cache MISS for key: {key}")
            return None
            
    except redis.RedisError as e:
        # Cache failures should never break the application
        logging.warning(f"Cache error (degraded mode): {e}")
        return None
```

**One-liner**: "A broken cache is an inconvenience; a broken app is a disaster."

## Cache Invalidation

**Default**: For LLM responses, rely on TTL expiration. For user data, invalidate on mutation.

```python
# ✅ Good: TTL-based expiration (LLM responses)
redis_client.setex(key, TTL_SECONDS, response)

# ✅ Good: Explicit invalidation (user data)
async def update_conversation(id: str, data: dict):
    await db.conversations.update_one({"id": id}, {"$set": data})
    redis_client.delete(f"conversation:{id}")  # Invalidate cache

# ❌ Bad: No invalidation strategy
await db.update(...)  # Cache now stale
```

## Connection Management

**Default**: Use connection pooling. Initialize Redis client at module level.

```python
# ✅ Good: Module-level client with connection pool
import redis

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=False,
    socket_connect_timeout=5,
    socket_timeout=5
)

# ❌ Bad: Creating new connection per request
def get_data():
    client = redis.Redis(...)  # Connection overhead per call
    return client.get(key)
```
