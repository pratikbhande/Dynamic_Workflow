"""MongoDB MCP - Complete Implementation"""
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from ...config import settings
import json

class MongoDBMCP:
    """MongoDB MCP for database operations"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB]
        self.connected = True
    
    async def insert_document(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a document"""
        try:
            result = await self.db[collection].insert_one(document)
            return f"Inserted document with ID: {result.inserted_id}"
        except Exception as e:
            return f"Error inserting document: {str(e)}"
    
    async def find_documents(self, collection: str, query: Dict[str, Any], limit: int = 10) -> str:
        """Find documents"""
        try:
            cursor = self.db[collection].find(query).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return json.dumps(documents, indent=2)
        except Exception as e:
            return f"Error finding documents: {str(e)}"
    
    async def update_document(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> str:
        """Update documents"""
        try:
            result = await self.db[collection].update_many(query, {"$set": update})
            return f"Updated {result.modified_count} documents"
        except Exception as e:
            return f"Error updating documents: {str(e)}"
    
    async def delete_documents(self, collection: str, query: Dict[str, Any]) -> str:
        """Delete documents"""
        try:
            result = await self.db[collection].delete_many(query)
            return f"Deleted {result.deleted_count} documents"
        except Exception as e:
            return f"Error deleting documents: {str(e)}"
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        return [
            {
                "name": "insert_document",
                "description": "Insert a document into MongoDB collection",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "document": {"type": "object"}
                    },
                    "required": ["collection", "document"]
                }
            },
            {
                "name": "find_documents",
                "description": "Find documents in MongoDB collection",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "query": {"type": "object"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["collection", "query"]
                }
            }
        ]