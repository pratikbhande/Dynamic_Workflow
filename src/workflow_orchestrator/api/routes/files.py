from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from ..schemas.file import UploadFileResponse, FileDetailsResponse, FileListResponse
from ...application.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])
file_service = FileService()


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload a file (Excel, CSV, or PDF)
    
    The file will be:
    1. Saved to disk
    2. Processed (extract columns, data, text)
    3. Stored in MongoDB with metadata
    
    Returns file_id and processed metadata
    """
    try:
        # Call file service with correct parameter name
        result = await file_service.upload_file(
            file=file.file,  # Pass the file object
            filename=file.filename,
            user_id=user_id
        )
        
        return UploadFileResponse(**result)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileDetailsResponse)
async def get_file(file_id: str):
    """
    Get file details by ID
    
    Returns complete file information including:
    - Metadata
    - Processed data (columns, rows)
    - Text content
    """
    try:
        file_details = await file_service.get_file(file_id)
        return FileDetailsResponse(**file_details)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=FileListResponse)
async def list_user_files(user_id: str):
    """
    List all files for a user
    
    Returns summary of all uploaded files
    """
    try:
        files = await file_service.list_user_files(user_id)
        
        return FileListResponse(
            user_id=user_id,
            total_files=len(files),
            files=files
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/inventory")
async def get_data_inventory(user_id: str):
    """
    Get formatted data inventory for all user files
    
    This shows:
    - File names and IDs
    - Column names
    - Sample data
    - Data types
    
    This is the exact format sent to the AI for workflow generation
    """
    try:
        inventory = await file_service.get_data_inventory(user_id)
        
        return {
            "user_id": user_id,
            "inventory": inventory
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    Delete a file
    
    Removes both the file from disk and the database record
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        import os
        
        db = await get_mongodb()
        
        # Get file record
        file_record = await db.get_collection("files").find_one({"id": file_id})
        if not file_record:
            raise ValueError(f"File {file_id} not found")
        
        # Delete file from disk
        file_path = file_record.get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        await db.get_collection("files").delete_one({"id": file_id})
        
        return {
            "status": "success",
            "message": f"File {file_id} deleted successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )