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
