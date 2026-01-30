from typing import Dict, Any
from .base import BaseFileProcessor
import pypdf

class PDFProcessor(BaseFileProcessor):
    """Process PDF files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                pages_text = []
                for page_num, page in enumerate(pdf_reader.pages):
                    pages_text.append({
                        "page_number": page_num + 1,
                        "text": page.extract_text()
                    })
                
                return {
                    "type": "pdf",
                    "data": {
                        "pages": pages_text,
                        "total_pages": len(pdf_reader.pages)
                    },
                    "metadata": {
                        "file_path": file_path,
                        "total_pages": len(pdf_reader.pages)
                    }
                }
        
        except Exception as e:
            return {
                "type": "pdf",
                "error": str(e),
                "metadata": {"file_path": file_path}
            }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract all text from PDF"""
        data = await self.process(file_path)
        
        if "error" in data:
            return f"Error processing PDF: {data['error']}"
        
        text_parts = []
        text_parts.append(f"PDF File: {file_path}")
        text_parts.append(f"Total Pages: {data['data']['total_pages']}\n")
        
        for page in data['data']['pages']:
            text_parts.append(f"\n=== Page {page['page_number']} ===")
            text_parts.append(page['text'])
        
        return "\n".join(text_parts)