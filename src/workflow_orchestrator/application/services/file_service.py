from typing import Dict, Any, BinaryIO
import uuid
import os
from datetime import datetime
import json
import shutil

from ...infrastructure.database.mongodb import get_mongodb
from ...infrastructure.file_processors.excel_processor import ExcelProcessor
from ...infrastructure.file_processors.csv_processor import CSVProcessor
from ...infrastructure.file_processors.pdf_processor import PDFProcessor
from ...config import settings


class FileService:
    """Application service for file operations"""
    
    def __init__(self):
        self.processors = {
            '.xlsx': ExcelProcessor(),
            '.xls': ExcelProcessor(),
            '.csv': CSVProcessor(),
            '.pdf': PDFProcessor()
        }
    
    async def upload_file(
        self,
        file: BinaryIO,  # This is a sync file object from FastAPI
        filename: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Upload and process a file"""
        
        # Generate unique file ID
        file_id = f"file_{uuid.uuid4().hex[:12]}"
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Create upload directory if not exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Save file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{file_ext}")
        
        # Use shutil.copyfileobj for sync file objects
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file, f)
        
        print(f"✅ File saved: {file_path}")
        
        # Process file
        processor = self.processors.get(file_ext)
        if not processor:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        processed_data = await processor.process(file_path)
        text_content = await processor.extract_text(file_path)
        
        print(f"✅ File processed: {len(text_content)} characters extracted")
        
        # Create file record with proper datetime handling
        file_record = {
            "id": file_id,
            "user_id": user_id,
            "original_filename": filename,
            "file_type": file_ext,
            "file_path": file_path,
            "processed_data": processed_data,
            "text_content": text_content,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Save to database
        db = await get_mongodb()
        await db.get_collection("files").insert_one(file_record)
        
        print(f"✅ File record saved to database: {file_id}")
        
        # Return serializable response
        return {
            "file_id": file_record["id"],
            "filename": file_record["original_filename"],
            "type": file_record["file_type"],
            "user_id": file_record["user_id"],
            "processed_data": file_record["processed_data"],
            "text_content": file_record["text_content"][:500] + "..." if len(file_record["text_content"]) > 500 else file_record["text_content"],
            "created_at": file_record["created_at"].isoformat(),
            "metadata": {
                "file_size": os.path.getsize(file_path),
                "file_path": file_path
            }
        }
    
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file details"""
        db = await get_mongodb()
        file_record = await db.get_collection("files").find_one({"id": file_id})
        
        if not file_record:
            raise ValueError(f"File {file_id} not found")
        
        # Convert MongoDB types to JSON serializable
        return self._serialize_file_record(file_record)
    
    async def list_user_files(self, user_id: str) -> list:
        """List all files for a user"""
        db = await get_mongodb()
        cursor = db.get_collection("files").find({"user_id": user_id})
        files = await cursor.to_list(length=100)
        
        # Convert all files to serializable format
        return [self._serialize_file_record(f) for f in files]
    
    async def get_data_inventory(self, user_id: str) -> str:
        """Get formatted inventory of all user data for workflow generation"""
        files = await self.list_user_files(user_id)
        
        if not files:
            return "No files uploaded yet."
        
        inventory_parts = []
        inventory_parts.append("DATA INVENTORY")
        inventory_parts.append("=" * 80)
        inventory_parts.append("")
        
        for idx, file_info in enumerate(files, 1):
            inventory_parts.append(f"FILE {idx}: {file_info['filename']}")
            inventory_parts.append(f"  ID: {file_info['file_id']}")
            inventory_parts.append(f"  Type: {file_info['type']}")
            inventory_parts.append(f"  Path: {file_info['file_path']}")
            
            # Add detailed structure
            processed = file_info.get('processed_data', {})
            
            if file_info['type'] in ['.xlsx', '.xls']:
                if 'sheets' in processed:
                    inventory_parts.append(f"  Excel File with {len(processed['sheets'])} sheet(s):")
                    for sheet_name, sheet_data in processed['sheets'].items():
                        inventory_parts.append(f"\n    Sheet: '{sheet_name}'")
                        inventory_parts.append(f"      Columns: {', '.join(sheet_data.get('columns', []))}")
                        inventory_parts.append(f"      Total Rows: {sheet_data.get('summary', {}).get('total_rows', 0)}")
                        
                        # Show sample data
                        sample_rows = sheet_data.get('rows', [])[:3]
                        if sample_rows:
                            inventory_parts.append(f"      Sample Data:")
                            for row in sample_rows:
                                inventory_parts.append(f"        {json.dumps(row)}")
            
            elif file_info['type'] == '.csv':
                if 'data' in processed:
                    data = processed['data']
                    inventory_parts.append(f"  CSV File:")
                    inventory_parts.append(f"    Columns: {', '.join(data.get('columns', []))}")
                    inventory_parts.append(f"    Total Rows: {data.get('summary', {}).get('total_rows', 0)}")
                    
                    # Show sample data
                    sample_rows = data.get('rows', [])[:3]
                    if sample_rows:
                        inventory_parts.append(f"    Sample Data:")
                        for row in sample_rows:
                            inventory_parts.append(f"      {json.dumps(row)}")
            
            elif file_info['type'] == '.pdf':
                if 'data' in processed:
                    data = processed['data']
                    inventory_parts.append(f"  PDF File:")
                    inventory_parts.append(f"    Total Pages: {data.get('total_pages', 0)}")
                    
                    # Show text preview
                    text_preview = file_info.get('text_content', '')[:300]
                    inventory_parts.append(f"    Content Preview:")
                    inventory_parts.append(f"      {text_preview}...")
            
            inventory_parts.append("")
            inventory_parts.append("-" * 80)
            inventory_parts.append("")
        
        return "\n".join(inventory_parts)
    
    def _serialize_file_record(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB file record to JSON serializable format"""
        
        # Remove MongoDB internal fields
        if '_id' in file_record:
            del file_record['_id']
        
        # Convert datetime objects to ISO strings
        for key in ['created_at', 'updated_at']:
            if key in file_record and file_record[key]:
                if isinstance(file_record[key], datetime):
                    file_record[key] = file_record[key].isoformat()
        
        # Return serializable format
        result = {
            "file_id": file_record.get("id"),
            "filename": file_record.get("original_filename"),
            "type": file_record.get("file_type"),
            "user_id": file_record.get("user_id"),
            "file_path": file_record.get("file_path"),
            "processed_data": file_record.get("processed_data", {}),
            "text_content": file_record.get("text_content", ""),
            "created_at": file_record.get("created_at"),
            "updated_at": file_record.get("updated_at")
        }
        
        return result