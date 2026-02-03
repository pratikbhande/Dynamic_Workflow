from langchain_core.tools import Tool
from typing import List
import aiofiles
import os
from ....config import settings

async def create_file_tools() -> List[Tool]:
    """Create tools for file operations"""
    
    async def read_file_func(filepath: str) -> str:
        """Read file contents - intelligently handles different file types"""
        try:
            full_path = os.path.join(settings.UPLOAD_DIR, filepath)
            
            # Check file extension
            ext = os.path.splitext(filepath)[1].lower()
            
            # For binary files (PDF, Excel), return metadata instead
            if ext in ['.pdf', '.xlsx', '.xls']:
                return f"Binary file: {filepath}. Use file processors or check files_context for extracted data."
            
            # For text files, read normally
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except UnicodeDecodeError:
            return f"Binary file: {filepath}. Cannot read as text. Check files_context for processed data."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def write_file_func(input_str: str) -> str:
        """Write content to file
        
        Input format: filepath|content
        """
        try:
            parts = input_str.split('|', 1)
            if len(parts) != 2:
                return "Error: Input must be in format 'filepath|content'"
            
            filepath, content = parts
            full_path = os.path.join(settings.UPLOAD_DIR, filepath)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
            
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def list_files_func(directory: str = ".") -> str:
        """List files in directory"""
        try:
            full_path = os.path.join(settings.UPLOAD_DIR, directory)
            files = os.listdir(full_path)
            return "Files:\n" + "\n".join(files)
        except Exception as e:
            return f"Error listing files: {str(e)}"
    
    return [
        Tool(
            name="read_file",
            description="Read contents of a TEXT file (.txt, .py, .json). Binary files return metadata.",
            func=lambda x: read_file_func(x),
            coroutine=read_file_func
        ),
        Tool(
            name="write_file",
            description="Write content to a file. Input format: 'filepath|content'",
            func=lambda x: write_file_func(x),
            coroutine=write_file_func
        ),
        Tool(
            name="list_files",
            description="List files in a directory. Input is the directory path (default: current directory).",
            func=lambda x: list_files_func(x),
            coroutine=list_files_func
        )
    ]