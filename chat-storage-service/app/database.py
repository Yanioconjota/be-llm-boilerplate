import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ollama")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Legacy collection for /save endpoint
collection = db["responses"]

# New collections for conversations
conversations_collection = db["conversations"]
messages_collection = db["messages"]

# Create indexes for better query performance
def ensure_indexes():
    """Create indexes for collections"""
    # Conversations: sort by updated_at for listing
    conversations_collection.create_index([("updated_at", DESCENDING)])
    conversations_collection.create_index([("id", ASCENDING)], unique=True)
    
    # Messages: query by conversation_id, sort by timestamp
    messages_collection.create_index([("conversation_id", ASCENDING), ("timestamp", ASCENDING)])
    messages_collection.create_index([("id", ASCENDING)], unique=True)

# Run on import
try:
    ensure_indexes()
except Exception as e:
    print(f"Warning: Could not create indexes: {e}")
