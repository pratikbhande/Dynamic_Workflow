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
    DEFAULT_VECTOR_DB: str = "chromadb"
    CHROMADB_PATH: str = "./data/chromadb"
    FAISS_PATH: str = "./data/faiss"
    
    # Storage
    UPLOAD_DIR: str = "./data/uploads"
    
    # MCP
    SLACK_BOT_TOKEN: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    
    # Credential Encryption (IMPORTANT!)
    CREDENTIAL_ENCRYPTION_KEY: Optional[str] = None
    
    # Advanced Features
    MAX_RETRY_ATTEMPTS: int = 5
    WORKFLOW_SIMILARITY_THRESHOLD: float = 0.85
    ENABLE_WORKFLOW_MEMORY: bool = True
    ENABLE_ERROR_LEARNING: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories
        os.makedirs(self.CHROMADB_PATH, exist_ok=True)
        os.makedirs(self.FAISS_PATH, exist_ok=True)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)


# Create global settings instance
settings = Settings()