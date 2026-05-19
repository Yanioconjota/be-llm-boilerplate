# Microservices Backend with Ollama LLM

A complete FastAPI microservices backend with Redis caching, MongoDB persistence, and Ollama LLM integration.

## Architecture

```
┌──────────────────┐     ┌───────────────────┐
│   FastAPI        │────▶│   Redis Cache     │
│   (Port 8000)    │     │   (Port 6379)     │
└────────┬─────────┘     └───────────────────┘
         │
         │ Cache MISS
         ▼
┌───────────────────┐
│   Ollama (Host)   │
│   (Port 11434)    │
└───────────────────┘
         │
         ▼
┌──────────────────┐     ┌───────────────────┐
│ Storage Service  │────▶│   MongoDB         │
│   (Port 8001)    │     │   (Port 27017)    │
└──────────────────┘     └───────────────────┘
```

**Flow**:
1. Client sends prompt to FastAPI `/ask`
2. FastAPI checks Redis cache (HIT → return immediately)
3. On MISS → call Ollama LLM → cache response → persist to MongoDB
4. Return response with `{ cached: true/false }` flag

## Prerequisites

1. **Docker Desktop** installed and running
2. **Ollama** installed on host machine:
   ```bash
   # Install from https://ollama.com
   ollama pull llama3
   ollama serve
   ```

## Project Structure

```
project-root/
├── docker-compose.yml
├── fast-api/
│   ├── app/
│   │   └── main.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   └── forward.py
│   ├── .env.template
│   ├── Dockerfile
│   └── requirements.txt
└── chat-storage-service/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── database.py
    │   ├── models.py
    │   └── routes/
    │       ├── __init__.py
    │       └── save.py
    ├── .env.template
    ├── Dockerfile
    └── requirements.txt
```

## Quick Start

1. **Clone the repository**

2. **Create environment files from templates**:
   ```bash
   cp fast-api/.env.template fast-api/.env
   cp chat-storage-service/.env.template chat-storage-service/.env
   ```

3. **Start Ollama on your host machine**:
   ```bash
   ollama serve
   ```

4. **Start all services**:
   ```bash
   docker-compose up --build
   ```

## Service URLs

| Service | URL |
|---------|-----|
| FastAPI Swagger | http://localhost:8000/docs |
| FastAPI ReDoc | http://localhost:8000/redoc |
| Storage Health | http://localhost:8001/health |
| RedisInsight UI | http://localhost:8002 |

## API Endpoints

### FastAPI (Port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/joker` | Demo: get a joke from Ollama |
| POST | `/ask` | Send prompt, get LLM response |

### Storage Service (Port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/save` | Save prompt/response pair |
| GET | `/health` | Check MongoDB connection |

## Usage Examples

```bash
# Test FastAPI health
curl http://localhost:8000/

# Test Storage health
curl http://localhost:8001/health

# Send a prompt (first call = cache miss)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'

# Same prompt again (cache hit, much faster)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'
```

## Response Format

```json
{
  "response": "The sky appears blue because...",
  "cached": false
}
```

- `cached: true` → Response from Redis (fast)
- `cached: false` → Fresh from Ollama (slower, now cached)

## Environment Variables

### FastAPI Service

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | App display name | FastAPI App |
| `APP_ENV` | Environment | development |
| `APP_HOST` | Bind address | 0.0.0.0 |
| `APP_PORT` | Bind port | 8000 |
| `OLLAMA_HOST` | Ollama server | http://host.docker.internal:11434 |
| `STORAGE_API_URL` | Storage endpoint | http://storage-service:8001/save |
| `REDIS_URL` | Redis connection | redis://redis:6379 |
| `CACHE_TTL` | Cache TTL (seconds) | 3600 |

### Storage Service

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection | mongodb://mongo:27017 |
| `DB_NAME` | Database name | ollama |
| `COLLECTION_NAME` | Collection name | responses |

## Docker Services

| Service | Container Name | Port |
|---------|----------------|------|
| FastAPI Gateway | ollama-api | 8000 |
| Storage Service | storage-api | 8001 |
| MongoDB | mongodb | 27017 |
| Redis | redis | 6379 |
| RedisInsight | redis-ui | 8002 |

## Development

To run with hot-reload enabled (default in development):

```bash
docker-compose up --build
```

The FastAPI service mounts the local directory as a volume, so changes to Python files will automatically reload the server.

## Troubleshooting

### Ollama Connection Issues

If FastAPI can't connect to Ollama:
1. Ensure Ollama is running on your host: `ollama serve`
2. Verify Ollama is accessible: `curl http://localhost:11434/api/tags`
3. Check that the `OLLAMA_HOST` env variable is correctly set

### Redis/MongoDB Issues

Check container logs:
```bash
docker-compose logs redis
docker-compose logs mongo
```

### Container Network Issues

Restart all containers:
```bash
docker-compose down
docker-compose up --build
```

## Author

Yanioconjota
