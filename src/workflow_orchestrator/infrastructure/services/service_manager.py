"""Service Manager - Deploy and manage long-running services"""
import subprocess
import socket
import time
import asyncio
import os
import signal
from typing import Dict, Any, Optional
from ...config import settings
import psutil

class ServiceManager:
    """Manages deployment of long-running services like Streamlit, Gradio"""
    
    def __init__(self):
        self.active_services: Dict[str, Dict[str, Any]] = {}
        self.port_range = range(8501, 8600)  # 100 ports available
        self.allocated_ports = set()
    
    def _find_available_port(self) -> int:
        """Find an available port"""
        for port in self.port_range:
            if port in self.allocated_ports:
                continue
            
            # Check if port is actually free
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    self.allocated_ports.add(port)
                    return port
                except OSError:
                    continue
        
        raise RuntimeError("No available ports in range 8501-8600")
    
    async def deploy_streamlit(
        self,
        app_code: str,
        service_id: str,
        app_name: str = "app"
    ) -> Dict[str, Any]:
        """Deploy a Streamlit application"""
        
        # Find available port
        port = self._find_available_port()
        
        # Create app file
        app_dir = os.path.join(settings.UPLOAD_DIR, f"service_{service_id}")
        os.makedirs(app_dir, exist_ok=True)
        
        app_file = os.path.join(app_dir, f"{app_name}.py")
        with open(app_file, 'w') as f:
            f.write(app_code)
        
        # Start Streamlit as background process
        process = subprocess.Popen(
            [
                'streamlit', 'run', app_file,
                '--server.port', str(port),
                '--server.headless', 'true',
                '--server.address', '0.0.0.0',
                '--browser.gatherUsageStats', 'false'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=app_dir,
            env={**os.environ, 'PYTHONPATH': settings.UPLOAD_DIR}
        )
        
        # Wait for service to start
        await self._wait_for_service(port, timeout=30)
        
        # Store service info
        service_info = {
            'service_id': service_id,
            'type': 'streamlit',
            'port': port,
            'pid': process.pid,
            'url': f"http://localhost:{port}",
            'app_file': app_file,
            'status': 'running'
        }
        
        self.active_services[service_id] = service_info
        
        return service_info
    
    async def deploy_gradio(
        self,
        app_code: str,
        service_id: str,
        app_name: str = "app"
    ) -> Dict[str, Any]:
        """Deploy a Gradio application"""
        
        # Find available port
        port = self._find_available_port()
        
        # Create app file with port injection
        app_dir = os.path.join(settings.UPLOAD_DIR, f"service_{service_id}")
        os.makedirs(app_dir, exist_ok=True)
        
        # Inject port into Gradio launch
        if '.launch()' in app_code:
            app_code = app_code.replace(
                '.launch()',
                f'.launch(server_port={port}, server_name="0.0.0.0", share=False)'
            )
        
        app_file = os.path.join(app_dir, f"{app_name}.py")
        with open(app_file, 'w') as f:
            f.write(app_code)
        
        # Start as background process
        process = subprocess.Popen(
            ['python', app_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=app_dir,
            env={**os.environ, 'PYTHONPATH': settings.UPLOAD_DIR}
        )
        
        # Wait for service to start
        await self._wait_for_service(port, timeout=30)
        
        # Store service info
        service_info = {
            'service_id': service_id,
            'type': 'gradio',
            'port': port,
            'pid': process.pid,
            'url': f"http://localhost:{port}",
            'app_file': app_file,
            'status': 'running'
        }
        
        self.active_services[service_id] = service_info
        
        return service_info
    
    async def deploy_flask(
        self,
        app_code: str,
        service_id: str,
        app_name: str = "app"
    ) -> Dict[str, Any]:
        """Deploy a Flask application"""
        
        # Find available port
        port = self._find_available_port()
        
        # Create app file
        app_dir = os.path.join(settings.UPLOAD_DIR, f"service_{service_id}")
        os.makedirs(app_dir, exist_ok=True)
        
        # Add port to Flask app
        if 'app.run()' in app_code:
            app_code = app_code.replace(
                'app.run()',
                f'app.run(host="0.0.0.0", port={port})'
            )
        elif 'if __name__' not in app_code:
            app_code += f'\n\nif __name__ == "__main__":\n    app.run(host="0.0.0.0", port={port})'
        
        app_file = os.path.join(app_dir, f"{app_name}.py")
        with open(app_file, 'w') as f:
            f.write(app_code)
        
        # Start Flask
        process = subprocess.Popen(
            ['python', app_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=app_dir,
            env={**os.environ, 'PYTHONPATH': settings.UPLOAD_DIR}
        )
        
        # Wait for service
        await self._wait_for_service(port, timeout=30)
        
        service_info = {
            'service_id': service_id,
            'type': 'flask',
            'port': port,
            'pid': process.pid,
            'url': f"http://localhost:{port}",
            'app_file': app_file,
            'status': 'running'
        }
        
        self.active_services[service_id] = service_info
        
        return service_info
    
    async def _wait_for_service(self, port: int, timeout: int = 30):
        """Wait for service to become available"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        print(f"✅ Service ready on port {port}")
                        return
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Service failed to start on port {port} within {timeout}s")
    
    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service info"""
        return self.active_services.get(service_id)
    
    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all active services"""
        return self.active_services.copy()
    
    def stop_service(self, service_id: str) -> bool:
        """Stop a running service"""
        service = self.active_services.get(service_id)
        if not service:
            return False
        
        try:
            # Kill process
            process = psutil.Process(service['pid'])
            process.terminate()
            process.wait(timeout=5)
            
            # Release port
            self.allocated_ports.discard(service['port'])
            
            # Remove from active services
            del self.active_services[service_id]
            
            print(f"✅ Stopped service {service_id}")
            return True
        
        except Exception as e:
            print(f"⚠️ Error stopping service {service_id}: {e}")
            return False
    
    def cleanup_all(self):
        """Stop all services"""
        service_ids = list(self.active_services.keys())
        for service_id in service_ids:
            self.stop_service(service_id)

# Global instance
_service_manager = ServiceManager()

def get_service_manager() -> ServiceManager:
    """Get the global service manager instance"""
    return _service_manager