from pypdf import PdfReader
from typing import Dict, Any


class PDFProcessor:
    """Process PDF files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process PDF file and extract text"""
        
        reader = PdfReader(file_path)
        
        pages_data = []
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            pages_data.append({
                "page_number": page_num,
                "text": text,
                "char_count": len(text)
            })
        
        return {
            "type": "pdf",
            "data": {
                "total_pages": len(reader.pages),
                "pages": pages_data
            }
        }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract all text from PDF for LLM context"""
        
        reader = PdfReader(file_path)
        
        text_parts = [f"PDF File: {file_path.split('/')[-1]}"]
        text_parts.append(f"Total Pages: {len(reader.pages)}\n")
        
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            text_parts.append(f"Page {page_num}:")
            text_parts.append(text)
            text_parts.append("\n")
        
        return "\n".join(text_parts)