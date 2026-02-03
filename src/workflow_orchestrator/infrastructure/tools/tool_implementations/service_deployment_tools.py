from langchain_core.tools import Tool
from typing import Dict, Any
import uuid
import ast
import subprocess
import sys
from ...services.service_manager import get_service_manager

def _clean_code_input(code: str) -> str:
    """Remove markdown code fences"""
    code = code.strip()
    
    # Remove opening fence
    opening_patterns = [
        "```python\n", "```python", "```py\n", "```py", "```\n", "```"
    ]
    for pattern in opening_patterns:
        if code.startswith(pattern):
            code = code[len(pattern):].strip()
            break
    
    # Remove closing fence
    if code.endswith("```"):
        code = code[:-3].strip()
    
    return code.strip()


def create_service_deployment_tools() -> list:
    """Create tools with dependency pre-installation"""
    
    service_manager = get_service_manager()
    
    def deploy_streamlit_func(code: str) -> str:
        """Deploy Streamlit with dependency pre-installation"""
        try:
            code = _clean_code_input(code)
            print(f"\n🔍 Analyzing Streamlit app dependencies...")
            
            # STEP 1: Extract imports from code
            imports = extract_imports(code)
            
            if imports:
                print(f"   Found imports: {', '.join(imports)}")
                
                # STEP 2: Install missing packages
                print(f"\n📥 Pre-installing dependencies...")
                for module in imports:
                    ensure_installed(module)
            
            # STEP 3: Deploy service
            print(f"\n🚀 Deploying Streamlit app...")
            
            import asyncio
            service_id = f"st_{uuid.uuid4().hex[:8]}"
            
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        service_manager.deploy_streamlit(code, service_id)
                    )
                    service_info = future.result(timeout=90)
            except RuntimeError:
                service_info = asyncio.run(
                    service_manager.deploy_streamlit(code, service_id)
                )
            
            return f"""✅ Streamlit deployed!

URL: {service_info['url']}
Service ID: {service_info['service_id']}

Open in browser: {service_info['url']}
"""
        
        except Exception as e:
            return f"❌ Deployment error: {str(e)}"
    
    def deploy_gradio_func(code: str) -> str:
        """Deploy Gradio with dependency pre-installation"""
        try:
            code = _clean_code_input(code)
            print(f"\n🔍 Analyzing Gradio app dependencies...")
            
            imports = extract_imports(code)
            
            if imports:
                print(f"   Found imports: {', '.join(imports)}")
                print(f"\n📥 Pre-installing dependencies...")
                for module in imports:
                    ensure_installed(module)
            
            print(f"\n🚀 Deploying Gradio app...")
            
            import asyncio
            service_id = f"gr_{uuid.uuid4().hex[:8]}"
            
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
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
            
            return f"""✅ Gradio deployed!

URL: {service_info['url']}
Service ID: {service_info['service_id']}

Open in browser: {service_info['url']}
"""
        
        except Exception as e:
            return f"❌ Deployment error: {str(e)}"
    
    def list_services_func(input_str: str = "") -> str:
        """List services"""
        services = service_manager.list_services()
        
        if not services:
            return "No services running"
        
        result = ["🚀 ACTIVE SERVICES\n"]
        for sid, info in services.items():
            result.append(f"Service: {sid}")
            result.append(f"  Type: {info['type']}")
            result.append(f"  URL: {info['url']}")
            result.append("")
        
        return "\n".join(result)
    
    return [
        Tool(
            name="deploy_streamlit",
            description="Deploy Streamlit app with auto dependency installation",
            func=deploy_streamlit_func
        ),
        Tool(
            name="deploy_gradio",
            description="Deploy Gradio app with auto dependency installation",
            func=deploy_gradio_func
        ),
        Tool(
            name="list_services",
            description="List running services",
            func=list_services_func
        )
    ]


def extract_imports(code: str) -> list:
    """Extract imports from code"""
    imports = set()
    
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except:
        import re
        for line in code.split('\n'):
            for pattern in [r'^\s*import\s+(\w+)', r'^\s*from\s+(\w+)\s+import']:
                match = re.match(pattern, line)
                if match:
                    imports.add(match.group(1))
    
    builtins = {
        'sys', 'os', 'io', 're', 'json', 'csv', 'math', 'random',
        'datetime', 'time', 'collections', 'itertools', 'functools',
        'pathlib', 'typing', 'streamlit', 'gradio'
    }
    
    return [imp for imp in imports if imp not in builtins]


def ensure_installed(module_name: str):
    """Ensure package is installed using AI"""
    
    # Check if installed
    try:
        __import__(module_name)
        print(f"   ✓ {module_name}")
        return
    except:
        print(f"   ✗ {module_name} - installing via AI...")
    
    # Ask AI for package name
    package = ask_ai_simple(module_name)
    
    if package:
        print(f"      💡 AI: {package}")
        
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package,
                 '--break-system-packages', '--quiet'],
                timeout=180,
                check=True
            )
            print(f"      ✅ Installed")
        except:
            print(f"      ⚠️  Install failed")


def ask_ai_simple(module_name: str) -> str:
    """Quick AI query for package name"""
    try:
        from openai import OpenAI
        from ....config import settings
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only the pip package name, one word."},
                {"role": "user", "content": f"Module: {module_name}"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        return response.choices[0].message.content.strip().split()[0]
    
    except:
        return module_name  # Fallback to module name
