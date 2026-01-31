from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseFileProcessor(ABC):
    """Base class for file processors"""
    
    @abstractmethod
    async def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process file and extract data
        
        Returns:
            {
                "type": "excel|csv|pdf",
                "data": {...},
                "metadata": {...}
            }
        """
        pass
    
    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """Extract text content from file"""
        pass