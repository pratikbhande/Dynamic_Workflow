from typing import Dict, Any
import os
import shutil
import uuid
from ...config import settings
from ...infrastructure.file_processors import FileProcessorFactory
from ...infrastructure.database.mongodb import get_mongodb

class FileService:
    """Service for file upload and processing"""
    
    async def upload_file(self, filename: str, file_content: bytes, user_id: str) -> Dict[str, Any]:
        """Upload and process file"""
        
        # Generate unique file ID
        file_id = f"file_{uuid.uuid4().hex[:12]}"
        file_extension = os.path.splitext(filename)[1]
        
        # Save file
        stored_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Process file
        try:
            processor = FileProcessorFactory.get_processor(file_extension)
            processed_data = await processor.process(file_path)
            text_content = await processor.extract_text(file_path)
            
            # Store in database
            file_record = {
                "id": file_id,
                "user_id": user_id,
                "original_filename": filename,
                "stored_filename": stored_filename,
                "file_type": file_extension,
                "file_path": file_path,
                "processed_data": processed_data,
                "text_content": text_content,
                "metadata": processed_data.get("metadata", {})
            }
            
            db = await get_mongodb()
            await db.get_collection("files").insert_one(file_record)
            
            return {
                "file_id": file_id,
                "filename": filename,
                "type": processed_data["type"],
                "metadata": processed_data.get("metadata", {}),
                "preview": text_content[:500] + "..." if len(text_content) > 500 else text_content
            }
        
        except Exception as e:
            # Cleanup file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"Error processing file: {str(e)}")
    
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file details"""
        db = await get_mongodb()
        file_record = await db.get_collection("files").find_one({"id": file_id})
        
        if not file_record:
            raise ValueError(f"File {file_id} not found")
        
        return file_record
    
    async def list_files(self, user_id: str) -> list:
        """List all files for a user"""
        db = await get_mongodb()
        cursor = db.get_collection("files").find({"user_id": user_id})
        files = await cursor.to_list(length=100)
        
        # Return simplified list
        return [
            {
                "file_id": f["id"],
                "filename": f["original_filename"],
                "type": f["file_type"],
                "metadata": f.get("metadata", {})
            }
            for f in files
        ]
    
    async def get_data_inventory(self, user_id: str) -> Dict[str, Any]:
        """Get complete data inventory for workflow generation"""
        files = await self.list_files(user_id)
        
        db = await get_mongodb()
        file_details = []
        
        for file_info in files:
            file_record = await db.get_collection("files").find_one({"id": file_info["file_id"]})
            if file_record:
                file_details.append({
                    "file_id": file_record["id"],
                    "filename": file_record["original_filename"],
                    "type": file_record["file_type"],
                    "data_summary": file_record["processed_data"],
                    "text_preview": file_record["text_content"][:300]
                })
        
        return {
            "total_files": len(files),
            "files": file_details
        }