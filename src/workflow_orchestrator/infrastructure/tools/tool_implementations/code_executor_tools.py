from langchain_core.tools import Tool
import sys
from io import StringIO
import traceback
import subprocess
import os
import re
from ....config import settings

def create_code_executor_tool() -> Tool:
    """Create tool for executing Python code with FULL auto pip install"""
    
    def execute_python(code: str) -> str:
        """
        Execute Python code with UNIVERSAL auto pip install
        
        Detects ALL import errors and auto-installs packages
        """
        try:
            # Create script file
            script_path = os.path.join(settings.UPLOAD_DIR, "temp_script.py")
            
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Execute with subprocess
            env = os.environ.copy()
            env['PYTHONPATH'] = settings.UPLOAD_DIR
            
            max_install_attempts = 5  # Prevent infinite loops
            attempt = 0
            
            while attempt < max_install_attempts:
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                    cwd=settings.UPLOAD_DIR
                )
                
                # Success!
                if result.returncode == 0:
                    # Cleanup
                    if os.path.exists(script_path):
                        os.remove(script_path)
                    
                    output = result.stdout
                    return f"Code executed successfully:\n{output}" if output else "Code executed successfully (no output)"
                
                # Check for import errors
                stderr = result.stderr
                
                # Detect ModuleNotFoundError or ImportError
                if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
                    # Extract package name
                    package_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", stderr)
                    if package_match:
                        package_name = package_match.group(1).split('.')[0]  # Get base package
                        
                        print(f"📦 Auto-installing missing package: {package_name}")
                        
                        # Install the package
                        install_result = subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', package_name, '--break-system-packages'],
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        if install_result.returncode == 0:
                            print(f"✅ Installed {package_name}, retrying...")
                            attempt += 1
                            continue  # Retry execution
                        else:
                            # Try common package name mappings
                            package_mappings = {
                                'PyPDF2': 'pypdf2',
                                'sklearn': 'scikit-learn',
                                'cv2': 'opencv-python',
                                'PIL': 'Pillow',
                                'bs4': 'beautifulsoup4'
                            }
                            
                            if package_name in package_mappings:
                                mapped_name = package_mappings[package_name]
                                print(f"📦 Trying mapped name: {mapped_name}")
                                
                                install_result = subprocess.run(
                                    [sys.executable, '-m', 'pip', 'install', mapped_name, '--break-system-packages'],
                                    capture_output=True,
                                    text=True,
                                    timeout=120
                                )
                                
                                if install_result.returncode == 0:
                                    print(f"✅ Installed {mapped_name}, retrying...")
                                    attempt += 1
                                    continue
                
                # If we get here, there's an error that's not a missing package
                # Cleanup and return error
                if os.path.exists(script_path):
                    os.remove(script_path)
                
                return f"Error executing code:\n{stderr}"
            
            # Max attempts exceeded
            if os.path.exists(script_path):
                os.remove(script_path)
            
            return f"Error: Could not resolve dependencies after {max_install_attempts} attempts"
        
        except subprocess.TimeoutExpired:
            if os.path.exists(script_path):
                os.remove(script_path)
            return "Error: Code execution timed out (60s limit)"
        except Exception as e:
            if os.path.exists(script_path):
                os.remove(script_path)
            error_trace = traceback.format_exc()
            return f"Error executing code:\n{error_trace}"
    
    return Tool(
        name="execute_python",
        description="""Execute Python code with UNIVERSAL auto package installation.
        
        Automatically detects and installs ANY missing package.
        File access: Can read/write files in /app/data/uploads/
        
        Input: Complete Python code as string
        Output: Execution result or error message
        
        Example:
        import pandas as pd
        df = pd.read_csv('/app/data/uploads/data.csv')
        print(df.head())
        """,
        func=execute_python
    )