from openai import AsyncOpenAI
from typing import List
from ...config import settings

class OpenAIClient:
    """OpenAI client for embeddings"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        return [item.embedding for item in response.data]
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embeddings = await self.get_embeddings([text])
        return embeddings[0]