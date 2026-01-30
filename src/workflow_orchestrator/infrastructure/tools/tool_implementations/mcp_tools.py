from langchain.tools import Tool
from typing import Dict, Any, List
import json

async def create_mcp_tools(mcp_client: Any) -> List[Tool]:
    """Create LangChain tools from MCP client"""
    
    tools = []
    mcp_tools = mcp_client.get_tools()
    
    for tool_spec in mcp_tools:
        tool_name = tool_spec["name"]
        
        # Create async function that calls MCP method
        async def mcp_func(input_str: str, method=tool_name) -> str:
            try:
                # Parse input as JSON
                params = json.loads(input_str) if input_str.startswith('{') else {"input": input_str}
                
                # Call MCP method
                method_func = getattr(mcp_client, method)
                result = await method_func(**params)
                
                return str(result)
            except Exception as e:
                return f"Error calling {method}: {str(e)}"
        
        tools.append(
            Tool(
                name=tool_name,
                description=tool_spec["description"],
                func=lambda x, m=tool_name: mcp_func(x, m),
                coroutine=lambda x, m=tool_name: mcp_func(x, m)
            )
        )
    
    return tools