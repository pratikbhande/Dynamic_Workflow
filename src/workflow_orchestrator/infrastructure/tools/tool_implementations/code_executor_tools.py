from langchain_core.tools import Tool
import sys
import traceback
import subprocess
import os
import ast
import json
from ....config import settings


def create_code_executor_tool() -> Tool:
    """Execute Python with 100% AI-powered package discovery"""
    
    def execute_python(code: str) -> str:
        """
        Execute Python with pure AI-based dependency resolution
        NO hardcoded mappings - AI figures out everything
        """
        try:
            # ✅ CLEAN MARKDOWN FENCES FIRST
            print(f"\n🔍 Step 1: Cleaning code input...")
            cleaned_code = _clean_code_input(code)
            
            original_len = len(code)
            cleaned_len = len(cleaned_code)
            print(f"   Original: {original_len} chars")
            print(f"   Cleaned: {cleaned_len} chars")
            
            if original_len != cleaned_len:
                print(f"   ✅ Removed markdown formatting")
            
            # Show first line for verification
            first_line = cleaned_code.split('\n')[0] if cleaned_code else ""
            print(f"   First line: {first_line[:80]}")
            
            print(f"\n🔍 Step 2: Analyzing imports...")
            imports = extract_all_imports(cleaned_code)
            
            if not imports:
                print(f"   No imports found")
            else:
                print(f"   Found {len(imports)} imports: {', '.join(imports)}")
                
                print(f"\n🔍 Step 3: Checking packages...")
                missing = []
                for module in imports:
                    if is_package_installed(module):
                        print(f"   ✓ {module}")
                    else:
                        print(f"   ✗ {module}")
                        missing.append(module)
                
                if missing:
                    print(f"\n📥 Step 4: Installing {len(missing)} packages via AI...")
                    for module in missing:
                        install_with_ai(module)
                else:
                    print(f"\n✅ Step 4: All packages installed")
            
            print(f"\n▶️  Step 5: Executing code...")
            print(f"=" * 60)
            result = execute_code_safely(cleaned_code)
            print(f"=" * 60)
            print(f"✅ Done\n")
            return result
        
        except Exception as e:
            return f"Error: {str(e)}\n{traceback.format_exc()}"
    
    return Tool(
        name="execute_python",
        description="Execute Python code with AI-powered auto-install",
        func=execute_python
    )


def _clean_code_input(code: str) -> str:
    """
    Remove markdown code fences from code input
    
    Handles:
    - ```python ... ```
    - ``` ... ```
    - Mixed formatting
    """
    code = code.strip()
    
    # Remove opening fence
    opening_patterns = [
        "```python\n",
        "```python",
        "```py\n",
        "```py",
        "```\n",
        "```"
    ]
    
    for pattern in opening_patterns:
        if code.startswith(pattern):
            code = code[len(pattern):].strip()
            break
    
    # Remove closing fence
    if code.endswith("```"):
        code = code[:-3].strip()
    
    # Handle case where there might be extra newlines
    code = code.strip()
    
    return code


def extract_all_imports(code: str) -> list:
    """Extract imports using AST"""
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
        # Regex fallback
        import re
        for line in code.split('\n'):
            for pattern in [r'^\s*import\s+(\w+)', r'^\s*from\s+(\w+)\s+import']:
                match = re.match(pattern, line)
                if match:
                    imports.add(match.group(1))
    
    # Filter builtins
    builtins = {
        'sys', 'os', 'io', 're', 'json', 'csv', 'math', 'random',
        'datetime', 'time', 'collections', 'itertools', 'functools',
        'pathlib', 'typing', 'copy', 'pickle', 'hashlib', 'uuid',
        'logging', 'warnings', 'traceback', 'subprocess', 'threading',
        'multiprocessing', 'asyncio', 'socket', 'http', 'urllib',
        'email', 'xml', 'html', 'sqlite3', 'argparse', 'configparser'
    }
    
    return [imp for imp in imports if imp not in builtins]


def is_package_installed(module_name: str) -> bool:
    """Check if package is installed"""
    try:
        __import__(module_name)
        return True
    except:
        return False


def install_with_ai(module_name: str):
    """
    Use ONLY AI to find and install package
    Pure AI discovery - no hardcoded mappings
    """
    print(f"\n   🤖 AI analyzing: {module_name}")
    
    # Check cache first (learned from previous AI responses)
    cached = get_cache(module_name)
    if cached:
        print(f"      💾 Using learned mapping: {cached}")
        if try_install(cached):
            print(f"      ✅ Installed: {cached}")
            return
    
    # Ask AI
    package_name = ask_ai_for_package(module_name)
    
    if package_name:
        print(f"      💡 AI suggests: {package_name}")
        
        # Try install
        if try_install(package_name):
            print(f"      ✅ Installed: {package_name}")
            save_cache(module_name, package_name)
            return
        
        # If failed, ask AI for alternatives
        print(f"      ⚠️  Install failed, asking for alternatives...")
        alt_package = ask_ai_for_alternative(module_name, package_name)
        
        if alt_package and alt_package != package_name:
            print(f"      💡 AI alternative: {alt_package}")
            if try_install(alt_package):
                print(f"      ✅ Installed: {alt_package}")
                save_cache(module_name, alt_package)
                return
    
    print(f"      ❌ Could not install {module_name}")


def ask_ai_for_package(module_name: str) -> str:
    """Ask GPT-4 for package name"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a Python package expert. 
Given a Python import module name, return ONLY the pip package name.
Return one word only - the exact package name for pip install.

Examples:
- cv2 → opencv-python
- PIL → Pillow
- sklearn → scikit-learn
- bs4 → beautifulsoup4

Return ONLY the package name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Module: {module_name}\nPackage name:"
                }
            ],
            max_tokens=20,
            temperature=0
        )
        
        package = response.choices[0].message.content.strip()
        package = package.replace('`', '').replace('"', '').replace("'", '').split()[0]
        return package
    
    except Exception as e:
        print(f"      ⚠️  AI query failed: {e}")
        return None


def ask_ai_for_alternative(module_name: str, failed_package: str) -> str:
    """Ask AI for alternative if first attempt failed"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Python package expert. Suggest alternative package names."
                },
                {
                    "role": "user",
                    "content": f"Module '{module_name}' import failed with package '{failed_package}'. What's an alternative pip package name? Return only the package name."
                }
            ],
            max_tokens=20,
            temperature=0.3
        )
        
        alt = response.choices[0].message.content.strip()
        alt = alt.replace('`', '').replace('"', '').replace("'", '').split()[0]
        return alt
    
    except:
        return None


def try_install(package_name: str) -> bool:
    """Try to install package"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package_name,
             '--break-system-packages', '--quiet', '--no-input'],
            capture_output=True,
            timeout=180
        )
        return result.returncode == 0
    except:
        return False


def get_cache(module: str) -> str:
    """Get cached mapping"""
    cache_file = os.path.join(settings.UPLOAD_DIR, '.ai_package_cache.json')
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f).get(module)
    except:
        pass
    return None


def save_cache(module: str, package: str):
    """Save learned mapping"""
    cache_file = os.path.join(settings.UPLOAD_DIR, '.ai_package_cache.json')
    try:
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        
        cache[module] = package
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
        
        print(f"      💾 Learned: {module} → {package}")
    except:
        pass


def execute_code_safely(code: str) -> str:
    """Execute code in subprocess"""
    script_path = os.path.join(settings.UPLOAD_DIR, "temp_exec.py")
    
    try:
        # Write the already-cleaned code
        with open(script_path, 'w') as f:
            f.write(code)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = settings.UPLOAD_DIR
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
            cwd=settings.UPLOAD_DIR
        )
        
        if os.path.exists(script_path):
            os.remove(script_path)
        
        if result.returncode == 0:
            return f"Output:\n{result.stdout}" if result.stdout.strip() else "Success (no output)"
        else:
            return f"Error:\n{result.stderr}"
    
    except Exception as e:
        if os.path.exists(script_path):
            os.remove(script_path)
        return f"Error: {str(e)}"