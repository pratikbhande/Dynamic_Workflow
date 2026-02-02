from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import importlib.util
import sys
import os

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    sources: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None


# Store chat handlers dynamically
_chat_handlers = {}


def register_chat_handler(execution_id: str, handler_path: str):
    """Register a chat handler for an execution"""
    _chat_handlers[execution_id] = handler_path


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Universal chat endpoint
    
    Dynamically loads and executes the chat logic created by chat_endpoint_builder agent
    """
    
    if not request.execution_id:
        raise HTTPException(
            status_code=400,
            detail="execution_id required. Execute a chatbot workflow first."
        )
    
    # Get handler path
    handler_path = _chat_handlers.get(request.execution_id)
    
    if not handler_path:
        raise HTTPException(
            status_code=404,
            detail=f"No chat handler found for execution {request.execution_id}. The workflow may not have created a chat endpoint."
        )
    
    try:
        # Dynamically import the chat handler
        spec = importlib.util.spec_from_file_location("chat_handler", handler_path)
        chat_module = importlib.util.module_from_spec(spec)
        sys.modules["chat_handler"] = chat_module
        spec.loader.exec_module(chat_module)
        
        # Call the handle_chat function
        if hasattr(chat_module, 'handle_chat'):
            result = await chat_module.handle_chat(
                message=request.message,
                context=request.context or {}
            )
            
            return ChatResponse(
                response=result.get('response', ''),
                sources=result.get('sources'),
                metadata=result.get('metadata')
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Chat handler missing 'handle_chat' function"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing chat handler: {str(e)}"
        )


@router.get("/handlers")
async def list_chat_handlers():
    """List all registered chat handlers"""
    return {
        "total_handlers": len(_chat_handlers),
        "handlers": [
            {"execution_id": exec_id, "handler_path": path}
            for exec_id, path in _chat_handlers.items()
        ]
    }