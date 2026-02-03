from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ...infrastructure.services.service_manager import get_service_manager

router = APIRouter(prefix="/services", tags=["services"])

@router.get("/")
async def list_services():
    """
    List all active services
    
    Returns information about deployed Streamlit/Gradio apps
    """
    try:
        service_manager = get_service_manager()
        services = service_manager.list_services()
        
        return {
            "total_services": len(services),
            "services": list(services.values())
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing services: {str(e)}"
        )


@router.get("/{service_id}")
async def get_service(service_id: str):
    """
    Get details of a specific service
    
    Returns URL, status, and metadata
    """
    try:
        service_manager = get_service_manager()
        service = service_manager.get_service(service_id)
        
        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"Service {service_id} not found"
            )
        
        return service
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting service: {str(e)}"
        )


@router.delete("/{service_id}")
async def stop_service(service_id: str):
    """
    Stop a running service
    
    Terminates the service process and frees the port
    """
    try:
        service_manager = get_service_manager()
        success = service_manager.stop_service(service_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Service {service_id} not found or already stopped"
            )
        
        return {
            "status": "success",
            "message": f"Service {service_id} stopped successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping service: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_all_services():
    """
    Stop all running services
    
    Use this to clean up all deployed apps
    """
    try:
        service_manager = get_service_manager()
        service_manager.cleanup_all()
        
        return {
            "status": "success",
            "message": "All services stopped"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up services: {str(e)}"
        )


@router.get("/health/{service_id}")
async def check_service_health(service_id: str):
    """
    Check if a service is running and accessible
    """
    try:
        import socket
        service_manager = get_service_manager()
        service = service_manager.get_service(service_id)
        
        if not service:
            raise HTTPException(
                status_code=404,
                detail=f"Service {service_id} not found"
            )
        
        # Check if port is accessible
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(('localhost', service['port']))
            healthy = result == 0
        
        return {
            "service_id": service_id,
            "healthy": healthy,
            "url": service['url'],
            "status": "running" if healthy else "unreachable"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking service health: {str(e)}"
        )