from typing import Literal
from .base import BaseVectorStore
from .chromadb_store import ChromaDBStore
from .faiss_store import FAISSStore

VectorDBType = Literal["chromadb", "faiss"]

class VectorStoreFactory:
    """Factory for creating vector stores"""
    
    @staticmethod
    def create(db_type: VectorDBType = "chromadb") -> BaseVectorStore:
        if db_type == "chromadb":
            return ChromaDBStore()
        elif db_type == "faiss":
            return FAISSStore()
        else:
            raise ValueError(f"Unknown vector DB type: {db_type}")