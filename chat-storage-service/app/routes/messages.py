from fastapi import APIRouter, HTTPException
from app.models import MessageCreate, Message
from app.database import conversations_collection, messages_collection
from pymongo.errors import PyMongoError
from datetime import datetime
from typing import List
import uuid

router = APIRouter()

MAX_MESSAGES_PER_CONVERSATION = 100


@router.post("/messages", response_model=Message)
def create_message(payload: MessageCreate):
    """Create a new message in a conversation"""
    try:
        # Check if conversation exists
        conv_doc = conversations_collection.find_one({"id": payload.conversation_id})
        if not conv_doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check message limit
        current_count = conv_doc.get("message_count", 0)
        if current_count >= MAX_MESSAGES_PER_CONVERSATION:
            raise HTTPException(
                status_code=400, 
                detail=f"Conversation has reached the maximum of {MAX_MESSAGES_PER_CONVERSATION} messages. Please start a new conversation."
            )
        
        # Create message
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=payload.conversation_id,
            role=payload.role,
            content=payload.content,
            timestamp=datetime.utcnow(),
            cached=payload.cached
        )
        
        messages_collection.insert_one(message.model_dump())
        
        # Update conversation's updated_at and message_count
        conversations_collection.update_one(
            {"id": payload.conversation_id},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$inc": {"message_count": 1}
            }
        )
        
        return message
        
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
def get_messages(conversation_id: str):
    """Get all messages for a conversation"""
    try:
        # Check if conversation exists
        conv_doc = conversations_collection.find_one({"id": conversation_id})
        if not conv_doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages sorted by timestamp
        cursor = messages_collection.find(
            {"conversation_id": conversation_id}
        ).sort("timestamp", 1)
        
        messages = []
        for doc in cursor:
            messages.append(Message(
                id=doc["id"],
                conversation_id=doc["conversation_id"],
                role=doc["role"],
                content=doc["content"],
                timestamp=doc["timestamp"],
                cached=doc.get("cached")
            ))
        
        return messages
        
    except HTTPException:
        raise
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
