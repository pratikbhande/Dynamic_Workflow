from langchain_core.tools import Tool
from typing import Dict, Any, List
import json
import inspect

async def create_mcp_tools(mcp_client: Any) -> List[Tool]:
    """Create LangChain tools from MCP client with proper parameter handling"""
    
    tools = []
    mcp_tools = mcp_client.get_tools()
    
    for tool_spec in mcp_tools:
        tool_name = tool_spec["name"]
        method_name = tool_name
        
        # Get the actual method
        if not hasattr(mcp_client, method_name):
            print(f"⚠️  MCP method {method_name} not found on client")
            continue
        
        method_func = getattr(mcp_client, method_name)
        
        # Inspect method signature to get parameter names
        sig = inspect.signature(method_func)
        param_names = [p for p in sig.parameters.keys() if p != 'self']
        
        # Create async function that calls MCP method with proper parameters
        async def mcp_func(input_str: str, method=method_name, params=param_names) -> str:
            try:
                method_func = getattr(mcp_client, method)
                
                # Parse input
                if input_str.startswith('{'):
                    # JSON input
                    parsed_input = json.loads(input_str)
                else:
                    # Single parameter - use first param name
                    if len(params) == 1:
                        parsed_input = {params[0]: input_str}
                    else:
                        parsed_input = {"input": input_str}
                
                # Call with unpacked kwargs
                result = await method_func(**parsed_input)
                
                return str(result)
            except TypeError as e:
                # Fallback for single parameter methods
                if len(params) == 1:
                    try:
                        result = await method_func(input_str)
                        return str(result)
                    except Exception as e2:
                        return f"Error calling {method}: {str(e2)}"
                return f"Error calling {method}: {str(e)}"
            except Exception as e:
                return f"Error calling {method}: {str(e)}"
        
        tools.append(
            Tool(
                name=tool_name,
                description=tool_spec["description"],
                func=lambda x, m=tool_name, p=param_names: mcp_func(x, m, p),
                coroutine=lambda x, m=tool_name, p=param_names: mcp_func(x, m, p)
            )
        )
    
    return tools