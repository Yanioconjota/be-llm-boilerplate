import os
import json
import logging
import requests
import asyncio
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from utils.forward import forward_to_storage
from utils.cache import get_cached_response, set_cached_response
from sse_starlette.sse import EventSourceResponse
import httpx
import traceback

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title=os.getenv("APP_NAME", "Default App"))
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ollama_url = f"{ollama_host}/api/generate"
# Get base storage URL (STORAGE_API_URL may include /save for legacy, so we strip it)
_storage_api = os.getenv("STORAGE_API_URL", "http://storage-service:8001")
storage_url = _storage_api.replace("/save", "") if _storage_api.endswith("/save") else _storage_api

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class PromptRequest(BaseModel):
    prompt: str


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    model: str = "llama3"


class StreamRequest(BaseModel):
    prompt: str


# ============================================================================
# Health & Legacy Endpoints
# ============================================================================

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


@app.post("/ask", summary="Ask with custom prompt (stateless)", description="Send a prompt to Ollama with Redis caching and MongoDB persistence. No conversation context.")
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


# ============================================================================
# Conversation Endpoints (Proxy to Storage Service)
# ============================================================================

@app.post("/conversations", summary="Create a new conversation")
async def create_conversation(payload: ConversationCreate):
    """Create a new conversation session"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{storage_url}/conversations",
                json=payload.model_dump()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations", summary="List all conversations")
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List all conversations with pagination"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{storage_url}/conversations",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", summary="Get conversation with messages")
async def get_conversation(conversation_id: str):
    """Get a conversation with all its messages"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{storage_url}/conversations/{conversation_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}", summary="Delete a conversation")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{storage_url}/conversations/{conversation_id}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logging.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SSE Streaming Endpoint
# ============================================================================

def build_context_prompt(messages: List[dict], new_prompt: str) -> str:
    """Build prompt with conversation history for Ollama"""
    context_parts = []
    
    # Take last 10 messages for context
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    
    for msg in recent_messages:
        prefix = "User: " if msg["role"] == "user" else "Assistant: "
        context_parts.append(f"{prefix}{msg['content']}")
    
    context_parts.append(f"User: {new_prompt}")
    context_parts.append("Assistant:")
    
    return "\n\n".join(context_parts)


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


async def save_message(conversation_id: str, role: str, content: str, cached: Optional[bool] = None):
    """Save a message to storage service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content
            }
            if cached is not None:
                payload["cached"] = cached
            
            response = await client.post(f"{storage_url}/messages", json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        raise


async def get_conversation_messages(conversation_id: str) -> List[dict]:
    """Get messages for a conversation from storage service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{storage_url}/conversations/{conversation_id}/messages")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Conversation not found")
        raise
    except Exception as e:
        logging.error(f"Error getting messages: {e}")
        raise


@app.post("/conversations/{conversation_id}/stream", summary="Send message and stream response (SSE)")
async def stream_conversation(conversation_id: str, request: StreamRequest):
    """
    Send a prompt to a conversation and stream the LLM response via Server-Sent Events.
    
    The response is a stream of SSE events:
    - `event: message` with `data: {"chunk": "token", "done": false, "cached": false}`
    - Final event: `data: {"chunk": "", "done": true, "cached": false}`
    - On error: `event: error` with `data: {"error": "type", "message": "description"}`
    """
    prompt = request.prompt.strip()
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    # Verify conversation exists and get messages for context
    try:
        messages = await get_conversation_messages(conversation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching conversation: {str(e)}")
    
    model = "llama3"
    
    async def event_generator():
        full_response = ""
        cached = False
        
        try:
            # Save user message first
            await save_message(conversation_id, "user", prompt)
            
            # Check cache for exact prompt (without context)
            cached_response = get_cached_response(prompt, model)
            
            if cached_response:
                logging.info(f"SSE: Cache HIT for conversation {conversation_id}")
                cached = True
                
                # Stream cached response word by word
                words = cached_response.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    full_response += chunk
                    yield {
                        "event": "message",
                        "data": json.dumps({"chunk": chunk, "done": False, "cached": True})
                    }
                    await asyncio.sleep(0.02)
                
            else:
                logging.info(f"SSE: Cache MISS for conversation {conversation_id} - streaming from Ollama")
                
                # Build context prompt with conversation history
                context_prompt = build_context_prompt(messages, prompt)
                
                try:
                    async for token in stream_from_ollama(context_prompt, model):
                        full_response += token
                        yield {
                            "event": "message",
                            "data": json.dumps({"chunk": token, "done": False, "cached": False})
                        }
                    
                    # Cache the response
                    set_cached_response(prompt, full_response, model)
                    
                except httpx.ConnectError:
                    logging.error("SSE: Ollama connection failed")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "llm_unavailable",
                            "message": "Cannot connect to Ollama. Ensure it is running with 'ollama serve'"
                        })
                    }
                    return
                    
                except httpx.TimeoutException:
                    logging.error("SSE: Ollama request timed out")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "error": "timeout",
                            "message": "Request timed out. Please try again."
                        })
                    }
                    return
            
            # Save assistant message
            await save_message(conversation_id, "assistant", full_response, cached=cached)
            
            # Send done event
            yield {
                "event": "message",
                "data": json.dumps({"chunk": "", "done": True, "cached": cached})
            }
            
            logging.info(f"SSE: Response completed ({len(full_response)} chars) for conversation {conversation_id}")
            
        except Exception as e:
            logging.error(f"SSE: Error in stream: {e}")
            traceback.print_exc()
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "internal",
                    "message": f"An error occurred: {str(e)}"
                })
            }
    
    return EventSourceResponse(event_generator())
