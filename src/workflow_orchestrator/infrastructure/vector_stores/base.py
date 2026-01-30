from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseVectorStore(ABC):
    """Abstract base for vector stores"""
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int = 1536) -> str:
        """Create collection and return collection name"""
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Add documents with embeddings"""
        pass
    
    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None:
        """Delete collection"""
        pass