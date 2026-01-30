import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
import uuid
from .base import BaseVectorStore
from ...config import settings

class ChromaDBStore(BaseVectorStore):
    """ChromaDB implementation"""
    
    def __init__(self):
        self.client = chromadb.Client(
            ChromaSettings(
                persist_directory=settings.CHROMADB_PATH,
                anonymized_telemetry=False
            )
        )
    
    async def create_collection(self, name: str, dimension: int = 1536) -> str:
        collection_name = f"{name}_{uuid.uuid4().hex[:8]}"
        self.client.create_collection(
            name=collection_name,
            metadata={"dimension": dimension}
        )
        return collection_name
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        collection = self.client.get_collection(collection_name)
        ids = [str(uuid.uuid4()) for _ in documents]
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    
    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        collection = self.client.get_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        return [
            {
                "document": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]
    
    async def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(collection_name)
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")