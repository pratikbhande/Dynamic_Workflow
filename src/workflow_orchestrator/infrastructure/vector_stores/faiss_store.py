import faiss
import numpy as np
from typing import List, Dict, Any
import uuid
import pickle
import os
from .base import BaseVectorStore
from ...config import settings

class FAISSStore(BaseVectorStore):
    """FAISS implementation"""
    
    def __init__(self):
        self.persist_directory = settings.FAISS_PATH
        os.makedirs(self.persist_directory, exist_ok=True)
        self.indexes: Dict[str, Dict] = {}
    
    async def create_collection(self, name: str, dimension: int = 1536) -> str:
        collection_name = f"{name}_{uuid.uuid4().hex[:8]}"
        
        index = faiss.IndexFlatL2(dimension)
        
        self.indexes[collection_name] = {
            "index": index,
            "documents": [],
            "metadatas": [],
            "dimension": dimension
        }
        
        return collection_name
    
    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        if collection_name not in self.indexes:
            raise ValueError(f"Collection {collection_name} not found")
        
        collection = self.indexes[collection_name]
        
        embeddings_array = np.array(embeddings).astype('float32')
        collection["index"].add(embeddings_array)
        
        collection["documents"].extend(documents)
        collection["metadatas"].extend(metadatas)
    
    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if collection_name not in self.indexes:
            raise ValueError(f"Collection {collection_name} not found")
        
        collection = self.indexes[collection_name]
        
        query_array = np.array([query_embedding]).astype('float32')
        distances, indices = collection["index"].search(query_array, top_k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(collection["documents"]):
                results.append({
                    "document": collection["documents"][idx],
                    "metadata": collection["metadatas"][idx],
                    "distance": float(dist)
                })
        
        return results
    
    async def delete_collection(self, collection_name: str) -> None:
        if collection_name in self.indexes:
            del self.indexes[collection_name]