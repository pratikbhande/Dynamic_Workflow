from .base import BaseFileProcessor
from .excel_processor import ExcelProcessor
from .csv_processor import CSVProcessor
from .pdf_processor import PDFProcessor
from .txt_processor import TXTProcessor

class FileProcessorFactory:
    @staticmethod
    def get_processor(file_extension: str) -> BaseFileProcessor:
        processors = {
            '.xlsx': ExcelProcessor(),
            '.xls': ExcelProcessor(),
            '.csv': CSVProcessor(),
            '.pdf': PDFProcessor(),
            '.txt': TXTProcessor()  # ADD THIS
        }
        
        processor = processors.get(file_extension.lower())
        if not processor:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        return processor