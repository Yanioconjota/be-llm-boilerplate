from fastapi import FastAPI
from app.routes import save, conversations, messages
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ollama Storage Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy route for backward compatibility
app.include_router(save.router)

# New conversation and message routes
app.include_router(conversations.router, tags=["conversations"])
app.include_router(messages.router, tags=["messages"])
