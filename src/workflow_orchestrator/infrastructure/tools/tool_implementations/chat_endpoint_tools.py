from langchain_core.tools import Tool
import os
import subprocess
import time
import socket
import sys
from ....config import settings


def create_chat_endpoint_tools() -> list:
    """Create tools for running FastAPI endpoints"""
    
    def run_chat_endpoint(code: str) -> str:
        """Save FastAPI code and RUN it as a background service"""
        try:
            # Find available port
            port = find_available_port(8100, 8200)
            
            # Ensure code has uvicorn runner
            if 'if __name__' not in code:
                code += f'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={port})
'''
            
            # Save code
            filename = f"chat_endpoint_{port}.py"
            filepath = os.path.join(settings.UPLOAD_DIR, filename)
            
            with open(filepath, 'w') as f:
                f.write(code)
            
            print(f"💾 Saved chat endpoint to: {filepath}")
            
            # Start as background process with output logging
            log_file = os.path.join(settings.UPLOAD_DIR, f"chat_endpoint_{port}.log")
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    [sys.executable, filepath],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=settings.UPLOAD_DIR,
                    env={**os.environ, 'PYTHONPATH': settings.UPLOAD_DIR}
                )
            
            print(f"🚀 Starting FastAPI on port {port}... (PID: {process.pid})")
            
            # Wait for it to start
            for i in range(15):
                time.sleep(1)
                if is_port_open('localhost', port):
                    return f"""✅ CHAT ENDPOINT RUNNING!

URL: http://localhost:{port}/chat
Health: http://localhost:{port}/health

Method: POST
Body: {{"message": "your question"}}

Example:
curl -X POST http://localhost:{port}/chat \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "What is this about?"}}'

Process ID: {process.pid}
Log file: {log_file}
"""
            
            return f"⚠️ Started but not responding yet. Check {log_file}"
        
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n{traceback.format_exc()}"
    
    return [
        Tool(
            name="run_chat_endpoint",
            description="Deploy FastAPI /chat endpoint as background service. Input: Complete FastAPI code",
            func=run_chat_endpoint
        )
    ]


def find_available_port(start: int, end: int) -> int:
    """Find available port"""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No ports available {start}-{end}")


def is_port_open(host: str, port: int) -> bool:
    """Check if port is open"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except:
            return False