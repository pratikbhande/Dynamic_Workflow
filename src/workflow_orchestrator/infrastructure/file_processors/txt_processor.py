from typing import Dict, Any
import aiofiles


class TXTProcessor:
    """Process TXT files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process TXT file"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        return {
            "type": "txt",
            "data": {
                "content": content,
                "lines": len(content.split('\n')),
                "chars": len(content)
            }
        }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()