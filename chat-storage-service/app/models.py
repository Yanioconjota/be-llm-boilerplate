from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional, List
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ResponsePayload(BaseModel):
    """Legacy model for backward compatibility with /save endpoint"""
    prompt: str
    response: str


class ConversationCreate(BaseModel):
    """Request body for creating a conversation"""
    title: Optional[str] = None
    model: str = "llama3"


class Conversation(BaseModel):
    """Conversation entity"""
    id: str = Field(default_factory=generate_uuid)
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = "llama3"
    message_count: int = 0


class ConversationSummary(BaseModel):
    """Conversation summary for list endpoint"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    model: str
    message_count: int


class ConversationList(BaseModel):
    """Paginated list of conversations"""
    items: List[ConversationSummary]
    total: int
    limit: int
    offset: int


class MessageCreate(BaseModel):
    """Request body for creating a message"""
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    cached: Optional[bool] = None


class Message(BaseModel):
    """Message entity"""
    id: str = Field(default_factory=generate_uuid)
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cached: Optional[bool] = None


class ConversationWithMessages(BaseModel):
    """Conversation with all its messages"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    model: str
    message_count: int
    messages: List[Message]
