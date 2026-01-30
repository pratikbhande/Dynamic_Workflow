import pandas as pd
from typing import Dict, Any
from .base import BaseFileProcessor
import json

class ExcelProcessor(BaseFileProcessor):
    """Process Excel files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process Excel file and extract all data"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Convert to dict
                sheets_data[sheet_name] = {
                    "columns": df.columns.tolist(),
                    "rows": df.to_dict('records'),
                    "shape": df.shape,
                    "summary": {
                        "total_rows": len(df),
                        "total_columns": len(df.columns),
                        "column_types": df.dtypes.astype(str).to_dict()
                    }
                }
            
            metadata = {
                "total_sheets": len(excel_file.sheet_names),
                "sheet_names": excel_file.sheet_names,
                "file_path": file_path
            }
            
            return {
                "type": "excel",
                "sheets": sheets_data,
                "metadata": metadata
            }
        
        except Exception as e:
            return {
                "type": "excel",
                "error": str(e),
                "metadata": {"file_path": file_path}
            }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text representation of Excel data"""
        data = await self.process(file_path)
        
        if "error" in data:
            return f"Error processing Excel file: {data['error']}"
        
        text_parts = []
        text_parts.append(f"Excel File: {file_path}")
        text_parts.append(f"Total Sheets: {data['metadata']['total_sheets']}\n")
        
        for sheet_name, sheet_data in data["sheets"].items():
            text_parts.append(f"\n=== Sheet: {sheet_name} ===")
            text_parts.append(f"Rows: {sheet_data['summary']['total_rows']}")
            text_parts.append(f"Columns: {', '.join(sheet_data['columns'])}")
            
            # Add sample data (first 5 rows)
            text_parts.append("\nSample Data:")
            for i, row in enumerate(sheet_data['rows'][:5]):
                text_parts.append(f"Row {i+1}: {json.dumps(row)}")
        
        return "\n".join(text_parts)