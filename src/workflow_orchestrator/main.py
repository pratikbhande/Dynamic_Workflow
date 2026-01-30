from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .infrastructure.database.mongodb import get_mongodb
from .api.routes import workflows_router, executions_router
from .api.routes.files import router as files_router

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
    print(f"\n{'='*60}")
    print(f"📡 Server ready at http://0.0.0.0:8000")
    print(f"📚 API docs at http://0.0.0.0:8000/docs")
    print(f"{'='*60}\n")
    
    yield
    
    # Shutdown
    print(f"\n{'='*60}")
    print(f"👋 Shutting down {settings.APP_NAME}")
    print(f"{'='*60}\n")
    
    db = await get_mongodb()
    await db.disconnect()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Dynamic Multi-Agent Workflow System with Full Context Awareness",
    version="0.1.0",
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

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "files": "/files",
            "workflows": "/workflows",
            "executions": "/executions"
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
        "openai_configured": bool(settings.OPENAI_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "workflow_orchestrator.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )