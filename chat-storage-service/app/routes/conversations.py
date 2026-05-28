from fastapi import APIRouter, HTTPException, Query
from app.models import (
    ConversationCreate, 
    Conversation, 
    ConversationSummary,
    ConversationList,
    ConversationWithMessages,
    Message
)
from app.database import conversations_collection, messages_collection
from pymongo.errors import PyMongoError
from datetime import datetime
import uuid

router = APIRouter()

MAX_MESSAGES_PER_CONVERSATION = 100


@router.post("/conversations", response_model=Conversation)
def create_conversation(payload: ConversationCreate):
    """Create a new conversation"""
    try:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=payload.title,
            model=payload.model,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=0
        )
        
        conversations_collection.insert_one(conversation.model_dump())
        return conversation
        
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List all conversations with pagination"""
    try:
        # Get total count
        total = conversations_collection.count_documents({})
        
        # Get paginated results, sorted by updated_at descending
        cursor = conversations_collection.find({}) \
            .sort("updated_at", -1) \
            .skip(offset) \
            .limit(limit)
        
        items = []
        for doc in cursor:
            items.append(ConversationSummary(
                id=doc["id"],
                title=doc.get("title"),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
                model=doc["model"],
                message_count=doc.get("message_count", 0)
            ))
        
        return ConversationList(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
def get_conversation(conversation_id: str):
    """Get a conversation with all its messages"""
    try:
        # Find conversation
        conv_doc = conversations_collection.find_one({"id": conversation_id})
        if not conv_doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages sorted by timestamp
        messages_cursor = messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", 1)
        
        messages = []
        for msg_doc in messages_cursor:
            messages.append(Message(
                id=msg_doc["id"],
                conversation_id=msg_doc["conversation_id"],
                role=msg_doc["role"],
                content=msg_doc["content"],
                timestamp=msg_doc["timestamp"],
                cached=msg_doc.get("cached")
            ))
        
        return ConversationWithMessages(
            id=conv_doc["id"],
            title=conv_doc.get("title"),
            created_at=conv_doc["created_at"],
            updated_at=conv_doc["updated_at"],
            model=conv_doc["model"],
            message_count=conv_doc.get("message_count", 0),
            messages=messages
        )
        
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages (hard delete)"""
    try:
        # Check if conversation exists
        conv_doc = conversations_collection.find_one({"id": conversation_id})
        if not conv_doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete all messages first
        messages_collection.delete_many({"conversation_id": conversation_id})
        
        # Delete conversation
        conversations_collection.delete_one({"id": conversation_id})
        
        return {"success": True}
        
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
