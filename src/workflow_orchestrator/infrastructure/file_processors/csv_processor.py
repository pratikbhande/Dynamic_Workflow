import pandas as pd
from typing import Dict, Any
import numpy as np
from datetime import datetime


class CSVProcessor:
    """Process CSV files"""
    
    async def process(self, file_path: str) -> Dict[str, Any]:
        """Process CSV file and extract structured data"""
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        return {
            "type": "csv",
            "data": {
                "columns": df.columns.tolist(),
                "rows": self._convert_to_serializable(df.to_dict('records')),
                "summary": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()}
                }
            }
        }
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text content from CSV for LLM context"""
        
        df = pd.read_csv(file_path)
        
        text_parts = [f"CSV File: {file_path.split('/')[-1]}"]
        text_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
        text_parts.append(f"Rows: {len(df)}\n")
        
        # Add sample rows (first 5)
        sample_rows = self._convert_to_serializable(df.head(5).to_dict('records'))
        for i, row in enumerate(sample_rows, 1):
            text_parts.append(f"Row {i}: {row}")
        
        return "\n".join(text_parts)
    
    def _convert_to_serializable(self, data: Any) -> Any:
        """Convert pandas/numpy types to JSON-serializable Python types"""
        if isinstance(data, dict):
            return {key: self._convert_to_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_serializable(item) for item in data]
        elif isinstance(data, pd.Timestamp):
            return data.isoformat()
        elif pd.isna(data):
            return None
        elif isinstance(data, (np.integer, np.int64, np.int32)):
            return int(data)
        elif isinstance(data, (np.floating, np.float64, np.float32)):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, (np.bool_, bool)):
            return bool(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data