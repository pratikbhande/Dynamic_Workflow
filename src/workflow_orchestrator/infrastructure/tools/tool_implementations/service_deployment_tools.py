from langchain_core.tools import Tool
from typing import Dict, Any
import uuid
import asyncio
import concurrent.futures
from ...services.service_manager import get_service_manager


def create_service_deployment_tools() -> list:
    """Create tools for deploying long-running services"""
    
    service_manager = get_service_manager()
    
    def deploy_streamlit_func(code: str) -> str:
        """
        Deploy a Streamlit application and return URL
        
        Input: Complete Streamlit Python code
        Output: URL where app is accessible
        """
        try:
            service_id = f"st_{uuid.uuid4().hex[:8]}"
            
            # FIX: Handle event loop properly for both sync and async contexts
            try:
                # Check if we're in an async context
                loop = asyncio.get_running_loop()
                
                # We're in async context, but tool is sync - use ThreadPoolExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        service_manager.deploy_streamlit(code, service_id)
                    )
                    service_info = future.result(timeout=90)
                    
            except RuntimeError:
                # No running loop - we can safely use asyncio.run()
                service_info = asyncio.run(
                    service_manager.deploy_streamlit(code, service_id)
                )
            
            return f"""✅ Streamlit app deployed successfully!

URL: {service_info['url']}
Service ID: {service_info['service_id']}
Status: {service_info['status']}

The app is now running and accessible at the URL above.
Use this URL to interact with your Streamlit application.

To stop the service later, use the service ID: {service_info['service_id']}
"""
        
        except concurrent.futures.TimeoutError:
            return f"❌ Error: Streamlit deployment timed out after 90 seconds"
        
        except Exception as e:
            import traceback
            return f"❌ Error deploying Streamlit app: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
    
    def deploy_gradio_func(code: str) -> str:
        """
        Deploy a Gradio application and return URL
        
        Input: Complete Gradio Python code
        Output: URL where app is accessible
        """
        try:
            service_id = f"gr_{uuid.uuid4().hex[:8]}"
            
            # FIX: Handle event loop properly
            try:
                loop = asyncio.get_running_loop()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        service_manager.deploy_gradio(code, service_id)
                    )
                    service_info = future.result(timeout=90)
                    
            except RuntimeError:
                service_info = asyncio.run(
                    service_manager.deploy_gradio(code, service_id)
                )
            
            return f"""✅ Gradio app deployed successfully!

URL: {service_info['url']}
Service ID: {service_info['service_id']}
Status: {service_info['status']}

The app is now running and accessible at the URL above.
Use this URL to interact with your Gradio interface.

To stop the service later, use the service ID: {service_info['service_id']}
"""
        
        except concurrent.futures.TimeoutError:
            return f"❌ Error: Gradio deployment timed out after 90 seconds"
        
        except Exception as e:
            import traceback
            return f"❌ Error deploying Gradio app: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
    
    def deploy_flask_func(code: str) -> str:
        """
        Deploy a Flask application and return URL
        
        Input: Complete Flask Python code
        Output: URL where app is accessible
        """
        try:
            service_id = f"flask_{uuid.uuid4().hex[:8]}"
            
            # FIX: Handle event loop properly
            try:
                loop = asyncio.get_running_loop()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        service_manager.deploy_flask(code, service_id)
                    )
                    service_info = future.result(timeout=90)
                    
            except RuntimeError:
                service_info = asyncio.run(
                    service_manager.deploy_flask(code, service_id)
                )
            
            return f"""✅ Flask app deployed successfully!

URL: {service_info['url']}
Service ID: {service_info['service_id']}
Status: {service_info['status']}

The app is now running and accessible at the URL above.

To stop the service later, use the service ID: {service_info['service_id']}
"""
        
        except concurrent.futures.TimeoutError:
            return f"❌ Error: Flask deployment timed out after 90 seconds"
        
        except Exception as e:
            import traceback
            return f"❌ Error deploying Flask app: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
    
    def list_services_func(input_str: str = "") -> str:
        """List all running services"""
        try:
            services = service_manager.list_services()
            
            if not services:
                return "No services currently running"
            
            result = ["🚀 ACTIVE SERVICES\n"]
            result.append(f"Total: {len(services)} service(s) running\n")
            
            for service_id, info in services.items():
                result.append(f"{'='*60}")
                result.append(f"Service ID: {service_id}")
                result.append(f"Type: {info['type']}")
                result.append(f"URL: {info['url']}")
                result.append(f"Port: {info['port']}")
                result.append(f"Status: {info['status']}")
                result.append(f"Process ID: {info['pid']}")
                result.append(f"App File: {info['app_file']}")
                result.append("")
            
            result.append(f"{'='*60}")
            result.append("\nTo stop a service, use: DELETE /services/<service_id>")
            
            return "\n".join(result)
        
        except Exception as e:
            return f"❌ Error listing services: {str(e)}"
    
    def stop_service_func(service_id: str) -> str:
        """Stop a running service"""
        try:
            success = service_manager.stop_service(service_id)
            
            if success:
                return f"✅ Successfully stopped service: {service_id}"
            else:
                return f"⚠️  Service {service_id} not found or already stopped"
        
        except Exception as e:
            return f"❌ Error stopping service: {str(e)}"
    
    return [
        Tool(
            name="deploy_streamlit",
            description="""Deploy a Streamlit application as a live service.
            
Input: Complete Python code for Streamlit app

Example input:
import streamlit as st
st.title("My App")
st.write("Hello World")

Output: URL where the app is accessible

The app will run as a background service on an available port (8501-8600).
""",
            func=deploy_streamlit_func
        ),
        Tool(
            name="deploy_gradio",
            description="""Deploy a Gradio application as a live service.
            
Input: Complete Python code for Gradio app

Example input:
import gradio as gr

def greet(name):
    return f"Hello {{name}}!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.launch()

Output: URL where the app is accessible

The app will run as a background service on an available port (8501-8600).
""",
            func=deploy_gradio_func
        ),
        Tool(
            name="deploy_flask",
            description="""Deploy a Flask application as a live service.
            
Input: Complete Python code for Flask app

Example input:
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

Output: URL where the app is accessible

The app will run as a background service on an available port (8501-8600).
""",
            func=deploy_flask_func
        ),
        Tool(
            name="list_services",
            description="""List all currently running services with their URLs and status.

Input: Empty string or any text (input is ignored)

Output: Formatted list of all active services including:
- Service IDs
- URLs
- Types (streamlit/gradio/flask)
- Status

Use this to check what services are currently running.
""",
            func=list_services_func
        ),
        Tool(
            name="stop_service",
            description="""Stop a running service by its service ID.

Input: Service ID (e.g., 'st_abc12345')

Output: Success or error message

Use this to stop a service that is no longer needed.
Get service IDs from list_services tool.
""",
            func=stop_service_func
        )
    ]