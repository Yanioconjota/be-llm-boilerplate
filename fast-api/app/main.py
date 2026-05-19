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
