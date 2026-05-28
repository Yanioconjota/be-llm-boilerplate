# Microservices Backend Boilerplate

> **Goal**: Create a complete FastAPI microservices backend with Redis caching, MongoDB persistence, and Ollama LLM integration. All code is provided — just create the files and run `docker-compose up --build`.

---

## Architecture Overview

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

---

## Prerequisites

1. **Docker Desktop** installed and running
2. **Ollama** installed on host machine:
```bash
# Install from https://ollama.com
ollama pull llama3
ollama serve
```

---

## Project Structure

```
project-root/
├── docker-compose.yml
├── test-websocket.html       # WebSocket test page (open in browser)
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

---

## Files to Create

### 1. `docker-compose.yml` (root)

```yaml
services:
  fastapi:
    build:
      context: ./fast-api
    container_name: ollama-api
    ports:
      - "8000:8000"
    env_file:
      - ./fast-api/.env
    volumes:
      - ./fast-api:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - storage-service
      - redis

  storage-service:
    build:
      context: ./chat-storage-service
    container_name: storage-api
    ports:
      - "8001:8001"
    env_file:
      - ./chat-storage-service/.env
    volumes:
      - ./chat-storage-service:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - mongo

  mongo:
    image: mongo:6
    container_name: mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    environment:
      MONGO_INITDB_DATABASE: ollama

  redis:
    image: redis:6-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  redis-ui:
    image: redis/redisinsight
    container_name: redis-ui
    ports:
      - "8002:5540"
    depends_on:
      - redis

volumes:
  mongo-data:
  redis-data:
```

### 2. `test-websocket.html` (root)

WebSocket test page - open in browser to test streaming responses.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Test - Ollama LLM</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }
        h1 { color: #00d9ff; }
        .status {
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .connected { background: #0f5132; color: #75b798; }
        .disconnected { background: #842029; color: #f5c2c7; }
        .connecting { background: #664d03; color: #ffda6a; }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #16213e;
            color: #eee;
            font-size: 16px;
            resize: vertical;
            min-height: 100px;
        }
        textarea:focus { outline: none; border-color: #00d9ff; }
        button {
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin: 10px 5px 10px 0;
            transition: all 0.2s;
        }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary { background: #00d9ff; color: #000; }
        .btn-primary:hover:not(:disabled) { background: #00b8d9; }
        .btn-secondary { background: #333; color: #fff; }
        .btn-secondary:hover:not(:disabled) { background: #444; }
        .btn-danger { background: #dc3545; color: #fff; }
        .btn-danger:hover:not(:disabled) { background: #bb2d3b; }
        .response-container {
            background: #16213e;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            min-height: 200px;
            white-space: pre-wrap;
            word-wrap: break-word;
            border: 2px solid #333;
        }
        .response-container.streaming { border-color: #00d9ff; }
        .meta {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            font-size: 14px;
            color: #888;
        }
        .meta span { background: #333; padding: 4px 8px; border-radius: 4px; }
        .cached { color: #ffc107 !important; }
        .fresh { color: #28a745 !important; }
        .error { color: #dc3545; background: #2c1215; padding: 10px; border-radius: 4px; }
        .logs {
            background: #0d1117;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            max-height: 150px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .logs div { margin: 2px 0; }
        .log-send { color: #58a6ff; }
        .log-receive { color: #7ee787; }
        .log-error { color: #f85149; }
        .log-info { color: #8b949e; }
    </style>
</head>
<body>
    <h1>🔌 WebSocket Test</h1>
    
    <div id="status" class="status disconnected">● Disconnected</div>
    
    <div>
        <button id="connectBtn" class="btn-primary" onclick="connect()">Connect</button>
        <button id="disconnectBtn" class="btn-danger" onclick="disconnect()" disabled>Disconnect</button>
    </div>

    <h3>Send Prompt</h3>
    <textarea id="prompt" placeholder="Enter your prompt here...">Tell me a short joke about programming</textarea>
    
    <div>
        <button id="sendBtn" class="btn-primary" onclick="sendPrompt()" disabled>Send</button>
        <button class="btn-secondary" onclick="clearResponse()">Clear</button>
    </div>

    <h3>Response <span id="streamingIndicator" style="display:none; color: #00d9ff;">● Streaming...</span></h3>
    <div id="response" class="response-container">Response will appear here...</div>
    
    <div class="meta">
        <span>Chunks: <strong id="chunkCount">0</strong></span>
        <span>Cached: <strong id="cachedStatus">-</strong></span>
        <span>Time: <strong id="responseTime">-</strong></span>
    </div>

    <h3>Connection Log</h3>
    <div id="logs" class="logs"></div>

    <script>
        let ws = null;
        let chunkCount = 0;
        let startTime = null;
        
        const statusEl = document.getElementById('status');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const sendBtn = document.getElementById('sendBtn');
        const promptEl = document.getElementById('prompt');
        const responseEl = document.getElementById('response');
        const chunkCountEl = document.getElementById('chunkCount');
        const cachedStatusEl = document.getElementById('cachedStatus');
        const responseTimeEl = document.getElementById('responseTime');
        const streamingIndicator = document.getElementById('streamingIndicator');
        const logsEl = document.getElementById('logs');

        function log(message, type = 'info') {
            const div = document.createElement('div');
            div.className = `log-${type}`;
            div.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logsEl.appendChild(div);
            logsEl.scrollTop = logsEl.scrollHeight;
        }

        function updateStatus(status) {
            statusEl.className = `status ${status}`;
            statusEl.textContent = status === 'connected' ? '● Connected' : 
                                   status === 'connecting' ? '◐ Connecting...' : '● Disconnected';
        }

        function connect() {
            if (ws) return;
            
            updateStatus('connecting');
            log('Connecting to ws://localhost:8000/ws/ask...', 'info');
            
            ws = new WebSocket('ws://localhost:8000/ws/ask');
            
            ws.onopen = () => {
                updateStatus('connected');
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                sendBtn.disabled = false;
                log('Connected successfully!', 'info');
            };
            
            ws.onclose = () => {
                updateStatus('disconnected');
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                sendBtn.disabled = true;
                streamingIndicator.style.display = 'none';
                ws = null;
                log('Connection closed', 'info');
            };
            
            ws.onerror = (error) => {
                log('WebSocket error - Is the server running?', 'error');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                log(`Received: ${JSON.stringify(data).substring(0, 100)}...`, 'receive');
                
                if (data.error) {
                    responseEl.innerHTML = `<div class="error">Error: ${data.message}</div>`;
                    streamingIndicator.style.display = 'none';
                    responseEl.classList.remove('streaming');
                    return;
                }
                
                if (data.chunk) {
                    responseEl.textContent += data.chunk;
                    chunkCount++;
                    chunkCountEl.textContent = chunkCount;
                }
                
                if (data.done) {
                    streamingIndicator.style.display = 'none';
                    responseEl.classList.remove('streaming');
                    sendBtn.disabled = false;
                    
                    cachedStatusEl.textContent = data.cached ? 'Yes ⚡' : 'No';
                    cachedStatusEl.className = data.cached ? 'cached' : 'fresh';
                    
                    const elapsed = Date.now() - startTime;
                    responseTimeEl.textContent = `${elapsed}ms`;
                    
                    log(`Complete! ${chunkCount} chunks, ${elapsed}ms, cached: ${data.cached}`, 'info');
                }
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
            }
        }

        function sendPrompt() {
            const prompt = promptEl.value.trim();
            if (!prompt || !ws) return;
            
            responseEl.textContent = '';
            responseEl.classList.add('streaming');
            chunkCount = 0;
            chunkCountEl.textContent = '0';
            cachedStatusEl.textContent = '-';
            responseTimeEl.textContent = '-';
            streamingIndicator.style.display = 'inline';
            sendBtn.disabled = true;
            startTime = Date.now();
            
            const message = JSON.stringify({ prompt });
            ws.send(message);
            log(`Sent: ${message}`, 'send');
        }

        function clearResponse() {
            responseEl.textContent = 'Response will appear here...';
            chunkCount = 0;
            chunkCountEl.textContent = '0';
            cachedStatusEl.textContent = '-';
            responseTimeEl.textContent = '-';
        }

        // Auto-connect on page load
        connect();
    </script>
</body>
</html>
```

---

## FastAPI Service (`fast-api/`)

### `fast-api/Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

CMD ["sh", "-c", "uvicorn app.main:app --host $APP_HOST --port $APP_PORT --reload"]
```

### `fast-api/requirements.txt`

```
fastapi
requests
python-dotenv
httpx
uvicorn[standard]
redis
```

### `fast-api/.env.template`

```
APP_NAME=FastAPI App
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
OLLAMA_HOST=http://host.docker.internal:11434
STORAGE_API_URL=http://storage-service:8001/save
REDIS_URL=redis://redis:6379
CACHE_TTL=3600
```

### `fast-api/app/main.py`

```python
import os
import json
import logging
import requests
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from utils.forward import forward_to_storage
from utils.cache import get_cached_response, set_cached_response
import httpx
import traceback

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=os.getenv("APP_NAME", "Default App"))
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_url = f"{ollama_host}/api/generate"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "app_name": os.getenv("APP_NAME"),
        "env": os.getenv("APP_ENV"),
        "host": os.getenv("APP_HOST"),
        "port": os.getenv("APP_PORT"),
        "message": "API is running"
    }

@app.get("/joker", summary="Get a joke from Ollama")
def ask_ollama():
    payload = {
        "model": "llama3",
        "prompt": "Please tell me a joke"
    }

    response = requests.post(ollama_url, json=payload, stream=True)

    output = ""
    for line in response.iter_lines():
        if line:
            try:
                data = line.decode("utf-8")
                chunk = json.loads(data)
                output += chunk.get("response", "")
            except Exception as e:
                print("Error decoding chunk:", e)

    return {"result": output}

class PromptRequest(BaseModel):
    prompt: str

@app.post("/ask", summary="Ask with custom prompt", description="Send a prompt to Ollama with Redis caching and MongoDB persistence.")
async def ask_ollama_dynamic(request: PromptRequest):
    model = "llama3"
    
    cached_response = get_cached_response(request.prompt, model)
    if cached_response:
        return {"response": cached_response, "cached": True}
    
    payload = {
        "model": model,
        "prompt": request.prompt,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(ollama_url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            result = data.get("response", "")

            set_cached_response(request.prompt, result, model)
            await forward_to_storage(prompt=request.prompt, response=result)

            return {"response": result, "cached": False}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logging.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")


manager = ConnectionManager()


async def stream_from_ollama(prompt: str, model: str = "llama3"):
    """Generator that streams responses from Ollama"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", ollama_url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line)
                        token = chunk_data.get("response", "")
                        done = chunk_data.get("done", False)
                        if token:
                            yield token
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue


@app.websocket("/ws/ask")
async def websocket_ask(websocket: WebSocket):
    """
    WebSocket endpoint for streaming LLM responses.
    
    Send: {"prompt": "your question here"}
    Receive: {"chunk": "token", "done": false, "cached": false}
             {"chunk": "", "done": true, "cached": false}
    
    Error: {"error": "error_type", "message": "description"}
    """
    await manager.connect(websocket)
    model = "llama3"
    
    try:
        while True:
            data = await websocket.receive_json()
            prompt = data.get("prompt", "").strip()
            
            if not prompt:
                await websocket.send_json({
                    "error": "validation",
                    "message": "Prompt cannot be empty"
                })
                continue
            
            logging.info(f"WebSocket received prompt: {prompt[:50]}...")
            
            cached_response = get_cached_response(prompt, model)
            if cached_response:
                logging.info("WebSocket: Cache HIT - streaming cached response")
                words = cached_response.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    await websocket.send_json({
                        "chunk": chunk,
                        "done": False,
                        "cached": True
                    })
                    await asyncio.sleep(0.02)
                
                await websocket.send_json({
                    "chunk": "",
                    "done": True,
                    "cached": True
                })
                continue
            
            logging.info("WebSocket: Cache MISS - streaming from Ollama")
            full_response = ""
            
            try:
                async for token in stream_from_ollama(prompt, model):
                    full_response += token
                    await websocket.send_json({
                        "chunk": token,
                        "done": False,
                        "cached": False
                    })
                
                set_cached_response(prompt, full_response, model)
                await forward_to_storage(prompt=prompt, response=full_response)
                
                await websocket.send_json({
                    "chunk": "",
                    "done": True,
                    "cached": False
                })
                logging.info(f"WebSocket: Response completed ({len(full_response)} chars)")
                
            except httpx.ConnectError:
                logging.error("WebSocket: Ollama connection failed")
                await websocket.send_json({
                    "error": "llm_unavailable",
                    "message": "Cannot connect to Ollama. Ensure it is running with 'ollama serve'"
                })
            except httpx.TimeoutException:
                logging.error("WebSocket: Ollama request timed out")
                await websocket.send_json({
                    "error": "timeout",
                    "message": "Request timed out. Please try again."
                })
            except Exception as e:
                logging.error(f"WebSocket: Error streaming from Ollama: {e}")
                await websocket.send_json({
                    "error": "internal",
                    "message": f"An error occurred: {str(e)}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info("WebSocket: Client disconnected")
    except Exception as e:
        manager.disconnect(websocket)
        logging.error(f"WebSocket: Unexpected error: {e}")
        traceback.print_exc()
```

### `fast-api/utils/__init__.py`

```python
# Empty file - marks directory as Python package
```

### `fast-api/utils/cache.py`

```python
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
```

### `fast-api/utils/forward.py`

```python
import os
import httpx
import logging

STORAGE_API_URL = os.getenv("STORAGE_API_URL")

async def forward_to_storage(prompt: str, response: str):
    payload = {"prompt": prompt, "response": response}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(STORAGE_API_URL, json=payload)
            r.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to store response: {e}")
```

---

## Storage Service (`chat-storage-service/`)

### `chat-storage-service/Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### `chat-storage-service/requirements.txt`

```
fastapi
uvicorn
pymongo
python-dotenv
```

### `chat-storage-service/.env.template`

```
MONGO_URI=mongodb://mongo:27017
DB_NAME=ollama
COLLECTION_NAME=responses
```

### `chat-storage-service/app/__init__.py`

```python
# Empty file - marks directory as Python package
```

### `chat-storage-service/app/main.py`

```python
from fastapi import FastAPI
from app.routes import save
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ollama Storage Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(save.router)
```

### `chat-storage-service/app/models.py`

```python
from pydantic import BaseModel

class ResponsePayload(BaseModel):
    prompt: str
    response: str
```

### `chat-storage-service/app/database.py`

```python
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ollama")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "responses")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
```

### `chat-storage-service/app/routes/__init__.py`

```python
# Empty file - marks directory as Python package
```

### `chat-storage-service/app/routes/save.py`

```python
from fastapi import APIRouter, HTTPException
from app.models import ResponsePayload
from app.database import collection
from pymongo.errors import PyMongoError

router = APIRouter()

@router.post("/save")
def save_response(payload: ResponsePayload):
    try:
        result = collection.insert_one(payload.dict())
        return {"status": "success", "inserted_id": str(result.inserted_id)}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/health")
def check_db_connection():
    try:
        count = collection.count_documents({})
        return {"status": "ok", "documents": count}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
```

---

## Run the Project

```bash
# Copy environment templates
cp fast-api/.env.template fast-api/.env
cp chat-storage-service/.env.template chat-storage-service/.env

# Start all services
docker-compose up --build

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8001/health

# Test prompt (first call = cache miss)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'

# Test prompt (second call = cache hit, much faster)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Why is the sky blue?"}'

# Test WebSocket (open in browser)
start test-websocket.html   # Windows
open test-websocket.html    # macOS
xdg-open test-websocket.html # Linux
```

---

## Service URLs

| Service | URL |
|---------|-----|
| FastAPI Swagger | http://localhost:8000/docs |
| FastAPI ReDoc | http://localhost:8000/redoc |
| Storage Health | http://localhost:8001/health |
| RedisInsight UI | http://localhost:8002 |

---

## API Endpoints

### FastAPI (Port 8000)

#### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/joker` | Demo: get a joke from Ollama |
| POST | `/ask` | Send prompt, get LLM response (full response) |

#### WebSocket Endpoint

| Protocol | Path | Description |
|----------|------|-------------|
| WS | `/ws/ask` | Stream LLM responses token-by-token |

**WebSocket Message Format:**
- **Send**: `{"prompt": "your question here"}`
- **Receive (chunk)**: `{"chunk": "token", "done": false, "cached": false}`
- **Receive (complete)**: `{"chunk": "", "done": true, "cached": false}`
- **Receive (error)**: `{"error": "error_type", "message": "description"}`

### Storage Service (Port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/save` | Save prompt/response pair |
| GET | `/health` | Check MongoDB connection |

---

## Response Format

```json
{
  "response": "The sky appears blue because...",
  "cached": false
}
```

- `cached: true` → Response from Redis (fast)
- `cached: false` → Fresh from Ollama (slower, now cached)

---

## Environment Variables Reference

### FastAPI

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

---

**Author**: Yanioconjota
