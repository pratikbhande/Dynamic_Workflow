from langchain.tools import Tool
import sys
from io import StringIO
import traceback
import subprocess
import os
from ....config import settings

def create_code_executor_tool() -> Tool:
    """Create tool for executing Python code with file access"""
    
    def execute_python(code: str) -> str:
        """
        Execute Python code with:
        - File system access
        - Common libraries (pandas, numpy, etc.)
        - Output capture
        """
        try:
            # Create a temporary script file
            script_path = os.path.join(settings.UPLOAD_DIR, "temp_script.py")
            
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Execute with subprocess for better isolation
            # Add upload directory to Python path so it can access files
            env = os.environ.copy()
            env['PYTHONPATH'] = settings.UPLOAD_DIR
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=settings.UPLOAD_DIR  # Run from upload directory
            )
            
            # Cleanup
            if os.path.exists(script_path):
                os.remove(script_path)
            
            if result.returncode == 0:
                output = result.stdout
                return f"Code executed successfully:\n{output}" if output else "Code executed successfully (no output)"
            else:
                return f"Error executing code:\n{result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Code execution timed out (30s limit)"
        except Exception as e:
            error_trace = traceback.format_exc()
            return f"Error executing code:\n{error_trace}"
    
    return Tool(
        name="execute_python",
        description="""Execute Python code with file access and common libraries.
        
        Available libraries: pandas, numpy, json, matplotlib, re, datetime
        File access: Can read/write files in /data/uploads/
        
        Input: Complete Python code as string
        Output: Execution result or error message
        
        Example:
        import pandas as pd
        import json
        
        df = pd.read_excel('/data/uploads/file_123.xlsx')
        result = df['Revenue'].sum()
        print(json.dumps({'total': float(result)}))
        """,
        func=execute_python
    )