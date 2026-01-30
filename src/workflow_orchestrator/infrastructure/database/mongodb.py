from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from ...config import settings

class MongoDB:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB]
        print(f"✅ Connected to MongoDB: {settings.MONGODB_DB}")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("✅ Disconnected from MongoDB")
    
    def get_collection(self, name: str):
        """Get collection"""
        return self.db[name]

# Global instance
_mongodb: Optional[MongoDB] = None

async def get_mongodb() -> MongoDB:
    """Get MongoDB instance"""
    global _mongodb
    if _mongodb is None:
        _mongodb = MongoDB()
        await _mongodb.connect()
    return _mongodb