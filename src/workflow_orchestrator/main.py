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
    print(f"✅ Web search: {'Enabled' if settings.TAVILY_API_KEY else 'Disabled (add TAVILY_API_KEY)'}")
    print(f"\n{'='*60}")
    print(f"📡 Server ready at http://0.0.0.0:8000")
    print(f"📚 API docs at http://0.0.0.0:8000/docs")
    print(f"{'='*60}\n")
    
    yield
    
    # Shutdown
    print(f"\n{'='*60}")
    print(f"👋 Shutting down {settings.APP_NAME}")
    print(f"Cleaning up services...")
    
    # Cleanup all services
    from .infrastructure.services.service_manager import get_service_manager
    service_manager = get_service_manager()
    service_manager.cleanup_all()
    
    print(f"{'='*60}\n")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="🤖 Intelligent Multi-Agent Workflow System with Self-Healing & Service Deployment",
    version="0.2.0",
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.2.0",
        "features": {
            "workflow_generation": "AI-powered with memory",
            "self_healing": "Automatic error recovery",
            "service_deployment": "Streamlit & Gradio apps",
            "report_generation": "PDF with charts",
            "web_search": "Solution finding"
        },
        "endpoints": {
            "docs": "/docs",
            "files": "/files",
            "workflows": "/workflows",
            "executions": "/executions",
            "services": "/services"
        }
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "vector_db": settings.DEFAULT_VECTOR_DB,
        "upload_directory": settings.UPLOAD_DIR,
        "openai_configured": bool(settings.OPENAI_API_KEY),
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