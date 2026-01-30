from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from ..schemas.file import UploadFileResponse, FileListResponse, DataInventoryResponse
from ...application.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])
file_service = FileService()

@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = "default_user"
):
    """Upload a file (Excel, CSV, PDF)"""
    try:
        content = await file.read()
        result = await file_service.upload_file(
            filename=file.filename,
            file_content=content,
            user_id=user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{file_id}")
async def get_file(file_id: str):
    """Get file details"""
    try:
        file_info = await file_service.get_file(file_id)
        return file_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=FileListResponse)
async def list_files(user_id: str):
    """List all files for a user"""
    try:
        files = await file_service.list_files(user_id)
        return FileListResponse(files=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}/inventory", response_model=DataInventoryResponse)
async def get_data_inventory(user_id: str):
    """Get complete data inventory for workflow generation"""
    try:
        inventory = await file_service.get_data_inventory(user_id)
        return inventory
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))