from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .infrastructure.database.mongodb import get_mongodb

from .api.routes.workflows import router as workflows_router
from .api.routes.executions import router as executions_router
from .api.routes.files import router as files_router
from .api.routes.services import router as services_router
from .api.routes.chat import router as chat_router
from .api.routes.credentials import router as credentials_router  # NEW

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(f"\n{'='*60}")
    print(f"🚀 Starting {settings.APP_NAME}")
    print(f"{'='*60}\n")
    
    # Connect to MongoDB
    await get_mongodb()
    
    print(f"✅ MongoDB connected")
    print(f"✅ Vector DB: {settings.DEFAULT_VECTOR_DB}")
    print(f"✅ Upload directory: {settings.UPLOAD_DIR}")
    print(f"✅ Self-healing: {settings.ENABLE_ERROR_LEARNING}")
    print(f"✅ Workflow memory: {settings.ENABLE_WORKFLOW_MEMORY}")
    
    # Load prompt library
    from .domain.prompts.prompt_library import get_prompt_library
    prompt_lib = get_prompt_library()
    print(f"✅ Prompt library: {len(prompt_lib.list_prompts())} prompts loaded")
    
    # Load predefined tools
    from .infrastructure.tools.tool_registry import ToolRegistry
    registry = ToolRegistry()
    print(f"✅ Predefined tools: {len(registry.list_predefined_tools())} tools loaded")
    
    print(f"\n{'='*60}")
    print(f"📡 Server ready at http://0.0.0.0:8000")
    print(f"📚 API docs at http://0.0.0.0:8000/docs")
    print(f"{'='*60}\n")
    
    yield
    
    # Shutdown
    print(f"\n{'='*60}")
    print(f"👋 Shutting down {settings.APP_NAME}")
    
    from .infrastructure.services.service_manager import get_service_manager
    service_manager = get_service_manager()
    service_manager.cleanup_all()
    
    print(f"{'='*60}\n")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="🤖 Intelligent Multi-Agent Workflow System with Predefined Tools & Credential Management",
    version="0.3.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflows_router)
app.include_router(executions_router)
app.include_router(files_router)
app.include_router(services_router)
app.include_router(chat_router)
app.include_router(credentials_router)  # NEW

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.3.0",
        "features": {
            "predefined_tools": ["rag_builder", "rag_chat", "report_generator", "web_search"],
            "workflow_generation": "AI-powered with prompt library",
            "credential_management": "Encrypted storage",
            "self_healing": "5-retry strategy with web search",
            "service_deployment": "Streamlit & Gradio apps",
            "vector_dbs": ["chromadb", "faiss", "pinecone"]
        },
        "endpoints": {
            "docs": "/docs",
            "files": "/files",
            "workflows": "/workflows",
            "executions": "/executions",
            "services": "/services",
            "credentials": "/credentials"
        }
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    from .infrastructure.tools.tool_registry import ToolRegistry
    from .domain.prompts.prompt_library import get_prompt_library
    
    registry = ToolRegistry()
    prompt_lib = get_prompt_library()
    
    return {
        "status": "healthy",
        "database": "connected",
        "vector_db": settings.DEFAULT_VECTOR_DB,
        "upload_directory": settings.UPLOAD_DIR,
        "predefined_tools": registry.list_predefined_tools(),
        "prompts_loaded": len(prompt_lib.list_prompts()),
        "features": {
            "self_healing": settings.ENABLE_ERROR_LEARNING,
            "workflow_memory": settings.ENABLE_WORKFLOW_MEMORY,
            "web_search": bool(getattr(settings, 'TAVILY_API_KEY', None)),
            "slack_notifications": bool(settings.SLACK_BOT_TOKEN)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )