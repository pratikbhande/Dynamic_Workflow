from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "workflow-orchestrator"
    DEBUG: bool = True
    
    # OpenAI (System LLM)
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "workflow_orchestrator"
    
    # Vector DB
    DEFAULT_VECTOR_DB: str = "chromadb"  # chromadb | faiss
    CHROMADB_PATH: str = "./data/chromadb"
    FAISS_PATH: str = "./data/faiss"
    
    # Storage
    UPLOAD_DIR: str = "./data/uploads"
    
    # MCP
    SLACK_BOT_TOKEN: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        os.makedirs(self.CHROMADB_PATH, exist_ok=True)
        os.makedirs(self.FAISS_PATH, exist_ok=True)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

settings = Settings()