"""API endpoints for credential management"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from ...domain.credentials.credential_manager import get_credential_manager

router = APIRouter(prefix="/credentials", tags=["credentials"])
credential_manager = get_credential_manager()


class StoreCredentialRequest(BaseModel):
    """Request to store credentials"""
    service_name: str
    credential_data: Dict[str, str]
    description: Optional[str] = None


class UpdateCredentialRequest(BaseModel):
    """Request to update credentials"""
    credential_data: Dict[str, str]


class CredentialResponse(BaseModel):
    """Credential response (without sensitive data)"""
    credential_id: str
    service_name: str
    description: Optional[str]
    credential_keys: List[str]
    created_at: str


@router.post("/store")
async def store_credential(
    request: StoreCredentialRequest,
    user_id: str = "default_user"
):
    """
    Store credentials for a service
    
    Example:
```json
    {
        "service_name": "openai",
        "credential_data": {
            "api_key": "sk-..."
        },
        "description": "OpenAI API key for embeddings"
    }
```
    
    Supported services:
    - openai: {"api_key": "sk-..."}
    - tavily: {"api_key": "tvly-..."}
    - pinecone: {"api_key": "...", "environment": "..."}
    - slack: {"bot_token": "xoxb-..."}
    """
    try:
        credential_id = await credential_manager.store_credential(
            user_id=user_id,
            service_name=request.service_name,
            credential_data=request.credential_data,
            description=request.description
        )
        
        return {
            "status": "success",
            "credential_id": credential_id,
            "service_name": request.service_name,
            "message": f"Credentials stored for {request.service_name}"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error storing credentials: {str(e)}"
        )


@router.get("/list")
async def list_credentials(user_id: str = "default_user"):
    """
    List all credentials for a user
    
    Returns metadata only (no sensitive data)
    """
    try:
        credentials = await credential_manager.list_user_credentials(user_id)
        
        return {
            "user_id": user_id,
            "total": len(credentials),
            "credentials": credentials
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing credentials: {str(e)}"
        )


@router.get("/validate/{service_name}")
async def validate_credential(
    service_name: str,
    user_id: str = "default_user"
):
    """
    Validate that credentials exist for a service
    
    Returns whether credentials are configured and what keys they have
    """
    try:
        # Get required keys for service
        required_keys_map = {
            "openai": ["api_key"],
            "tavily": ["api_key"],
            "pinecone": ["api_key"],
            "slack": ["bot_token"]
        }
        
        required_keys = required_keys_map.get(service_name, [])
        
        is_valid, error = await credential_manager.validate_credential(
            user_id=user_id,
            service_name=service_name,
            required_keys=required_keys
        )
        
        return {
            "service_name": service_name,
            "valid": is_valid,
            "error": error,
            "required_keys": required_keys
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating credentials: {str(e)}"
        )


@router.put("/{credential_id}")
async def update_credential(
    credential_id: str,
    request: UpdateCredentialRequest
):
    """
    Update existing credentials
    
    Use this to rotate API keys or update credentials
    """
    try:
        success = await credential_manager.update_credential(
            credential_id=credential_id,
            credential_data=request.credential_data
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Credential {credential_id} not found"
            )
        
        return {
            "status": "success",
            "credential_id": credential_id,
            "message": "Credentials updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating credentials: {str(e)}"
        )


@router.delete("/{service_name}")
async def delete_credential(
    service_name: str,
    user_id: str = "default_user"
):
    """
    Delete credentials for a service
    """
    try:
        success = await credential_manager.delete_credential(
            user_id=user_id,
            service_name=service_name
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"No credentials found for {service_name}"
            )
        
        return {
            "status": "success",
            "service_name": service_name,
            "message": f"Credentials deleted for {service_name}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting credentials: {str(e)}"
        )


@router.post("/system/setup")
async def setup_system_credentials():
    """
    Setup system credentials from environment variables
    
    This is a helper endpoint to load credentials from .env
    Useful for initial setup
    """
    try:
        from ....config import settings
        
        setup_results = []
        
        # OpenAI
        if settings.OPENAI_API_KEY:
            cred_id = await credential_manager.store_credential(
                user_id="system",
                service_name="openai",
                credential_data={"api_key": settings.OPENAI_API_KEY},
                description="System OpenAI API key from environment"
            )
            setup_results.append({"service": "openai", "status": "configured", "credential_id": cred_id})
        
        # Tavily
        if hasattr(settings, 'TAVILY_API_KEY') and settings.TAVILY_API_KEY:
            cred_id = await credential_manager.store_credential(
                user_id="system",
                service_name="tavily",
                credential_data={"api_key": settings.TAVILY_API_KEY},
                description="System Tavily API key from environment"
            )
            setup_results.append({"service": "tavily", "status": "configured", "credential_id": cred_id})
        
        # Slack
        if settings.SLACK_BOT_TOKEN:
            cred_id = await credential_manager.store_credential(
                user_id="system",
                service_name="slack",
                credential_data={"bot_token": settings.SLACK_BOT_TOKEN},
                description="System Slack bot token from environment"
            )
            setup_results.append({"service": "slack", "status": "configured", "credential_id": cred_id})
        
        return {
            "status": "success",
            "configured_services": len(setup_results),
            "results": setup_results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error setting up system credentials: {str(e)}"
        )