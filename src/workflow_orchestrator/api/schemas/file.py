from pydantic import BaseModel
from typing import Dict, Any, List

class UploadFileResponse(BaseModel):
    file_id: str
    filename: str
    type: str
    metadata: Dict[str, Any]
    preview: str

class FileListResponse(BaseModel):
    files: List[Dict[str, Any]]

class DataInventoryResponse(BaseModel):
    total_files: int
    files: List[Dict[str, Any]]