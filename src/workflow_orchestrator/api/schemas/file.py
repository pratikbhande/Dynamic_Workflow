from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class UploadFileResponse(BaseModel):
    file_id: str
    filename: str
    type: str
    user_id: str
    processed_data: Dict[str, Any]
    text_content: str
    created_at: str
    metadata: Dict[str, Any]


class FileDetailsResponse(BaseModel):
    file_id: str
    filename: str
    type: str
    user_id: str
    file_path: str
    processed_data: Dict[str, Any]
    text_content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FileListResponse(BaseModel):
    user_id: str
    total_files: int
    files: List[Dict[str, Any]]