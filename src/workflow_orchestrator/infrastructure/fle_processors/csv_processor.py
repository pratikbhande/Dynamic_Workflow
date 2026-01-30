import pandas as pd
from typing import Dict, Any
from .base import BaseFileProcessor

class CSVProcessor(BaseFileProcessor):
    """Process CSV files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            return {
                "type": "csv",
                "data": {
                    "columns": df.columns.tolist(),
                    "rows": df.to_dict('records'),
                    "shape": df.shape,
                    "summary": {
                        "total_rows": len(df),
                        "total_columns": len(df.columns),
                        "column_types": df.dtypes.astype(str).to_dict(),
                        "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
                        "text_columns": df.select_dtypes(include=['object']).columns.tolist()
                    }
                },
                "metadata": {"file_path": file_path}
            }
        
        except Exception as e:
            return {
                "type": "csv",
                "error": str(e),
                "metadata": {"file_path": file_path}
            }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text from CSV"""
        data = await self.process(file_path)
        
        if "error" in data:
            return f"Error processing CSV: {data['error']}"
        
        text_parts = []
        text_parts.append(f"CSV File: {file_path}")
        text_parts.append(f"Rows: {data['data']['summary']['total_rows']}")
        text_parts.append(f"Columns: {', '.join(data['data']['columns'])}\n")
        
        text_parts.append("Sample Data (first 5 rows):")
        for i, row in enumerate(data['data']['rows'][:5]):
            text_parts.append(f"Row {i+1}: {row}")
        
        return "\n".join(text_parts)