from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from ...config import settings


class MongoDB:
    """MongoDB database connection"""
    
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        if self.client is None:
            print(f"Connecting to MongoDB: {settings.MONGODB_URL}")
            
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            
            self.db = self.client[settings.MONGODB_DB]
            
            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {settings.MONGODB_DB}")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("✅ Disconnected from MongoDB")
    
    def get_collection(self, name: str):
        """Get a collection"""
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db[name]


# Global instance
_mongodb = MongoDB()


async def get_mongodb() -> MongoDB:
    """Get MongoDB instance"""
    if _mongodb.client is None:
        await _mongodb.connect()
    return _mongodb