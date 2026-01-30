"""Filesystem MCP - Complete Implementation"""
import os
import aiofiles
from typing import Dict, Any, List
from ...config import settings

class FilesystemMCP:
    """Filesystem MCP for file operations"""
    
    def __init__(self):
        self.base_path = settings.UPLOAD_DIR
        self.connected = True
    
    async def read_file(self, filepath: str) -> str:
        """Read file contents"""
        try:
            full_path = os.path.join(self.base_path, filepath)
            async with aiofiles.open(full_path, 'r') as f:
                content = await f.read()
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def write_file(self, filepath: str, content: str) -> str:
        """Write content to file"""
        try:
            full_path = os.path.join(self.base_path, filepath)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
            
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def list_files(self, directory: str = ".") -> List[str]:
        """List files in directory"""
        try:
            full_path = os.path.join(self.base_path, directory)
            files = os.listdir(full_path)
            return files
        except Exception as e:
            return [f"Error: {str(e)}"]
    
    async def delete_file(self, filepath: str) -> str:
        """Delete a file"""
        try:
            full_path = os.path.join(self.base_path, filepath)
            os.remove(full_path)
            return f"Successfully deleted {filepath}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"
    
    async def file_exists(self, filepath: str) -> bool:
        """Check if file exists"""
        full_path = os.path.join(self.base_path, filepath)
        return os.path.exists(full_path)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        return [
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path to file"}
                    },
                    "required": ["filepath"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["filepath", "content"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "default": "."}
                    }
                }
            }
        ]