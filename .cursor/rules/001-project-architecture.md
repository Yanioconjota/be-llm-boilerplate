# Project Architecture Rules

## Microservices Structure

**Default**: Each service is a self-contained Docker container with its own:
- `Dockerfile`
- `requirements.txt` (Python) or `package.json` (Node)
- `.env.template` file (never `.env` in git)
- `/app` folder containing the application code

**Rationale**:
1. Services can be deployed and scaled independently
2. Technology choices are isolated per service
3. Environment templates ensure configuration documentation without exposing secrets

## Service Communication

**Default**: Services communicate via HTTP REST internally, SSE for client streaming.

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION PATTERNS                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Client → API Gateway                                            │
│  ├── REST (JSON)      → CRUD operations                          │
│  └── SSE (streaming)  → Real-time LLM responses                  │
│                                                                  │
│  Service → Service                                               │
│  └── REST (JSON)      → Internal data exchange                   │
│                                                                  │
│  Service → Database                                              │
│  └── Native drivers   → MongoDB, Redis                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Exceptions**:
- Use WebSockets only if bidirectional real-time communication is required
- gRPC for high-throughput internal service communication (document the need)

## Folder Structure Convention

```
service-name/
├── Dockerfile
├── requirements.txt
├── .env.template
└── app/
    ├── main.py           # FastAPI app, routes
    ├── models.py         # Pydantic models
    ├── database.py       # Database connections
    ├── routes/           # Route modules (for large services)
    │   └── feature.py
    └── utils/            # Shared utilities
        └── helpers.py
```

## Environment Variables

**Default**: Use `.env.template` files with placeholder values, never commit actual `.env` files.

```bash
# .env.template example
MONGO_URI=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
API_PORT=8000
```

**Anti-Patterns**:
- ❌ Hardcoding connection strings
- ❌ Committing `.env` files
- ❌ Using different variable names per environment
