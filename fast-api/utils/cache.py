import os
import hashlib
import logging
from typing import Optional
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))

_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            _redis_client.ping()
            logging.info("Connected to Redis")
        except redis.ConnectionError as e:
            logging.warning(f"Redis not available, caching disabled: {e}")
            return None
    return _redis_client


def generate_cache_key(prompt: str, model: str = "llama3") -> str:
    content = f"{model}:{prompt}"
    return f"ollama:{hashlib.sha256(content.encode()).hexdigest()}"


def get_cached_response(prompt: str, model: str = "llama3") -> Optional[str]:
    client = get_redis_client()
    if client is None:
        return None
    
    try:
        key = generate_cache_key(prompt, model)
        cached = client.get(key)
        if cached:
            logging.info(f"Cache HIT for key: {key[:20]}...")
            return cached
        logging.info(f"Cache MISS for key: {key[:20]}...")
        return None
    except redis.RedisError as e:
        logging.error(f"Redis error on get: {e}")
        return None


def set_cached_response(prompt: str, response: str, model: str = "llama3", ttl: int = None) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    
    try:
        key = generate_cache_key(prompt, model)
        ttl = ttl or CACHE_TTL
        client.setex(key, ttl, response)
        logging.info(f"Cached response for key: {key[:20]}... (TTL: {ttl}s)")
        return True
    except redis.RedisError as e:
        logging.error(f"Redis error on set: {e}")
        return False


def clear_cache(pattern: str = "ollama:*") -> int:
    client = get_redis_client()
    if client is None:
        return 0
    
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except redis.RedisError as e:
        logging.error(f"Redis error on clear: {e}")
        return 0
