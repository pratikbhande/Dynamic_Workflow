"""WebSearch MCP - Complete Implementation with Tavily"""
from typing import Dict, Any, List
import httpx
from ...config import settings

class WebSearchMCP:
    """Web Search MCP for finding solutions and information"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'TAVILY_API_KEY', None)
        self.connected = bool(self.api_key)
    
    async def search(self, query: str, max_results: int = 5) -> str:
        """Search the web for information"""
        if not self.connected:
            return "Web search not configured (no Tavily API key). Get free key at https://tavily.com"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True,
                        "search_depth": "advanced"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Format results
                    results = []
                    
                    # Add answer if available
                    if data.get("answer"):
                        results.append(f"ANSWER: {data['answer']}\n")
                    
                    # Add search results
                    for idx, result in enumerate(data.get("results", []), 1):
                        results.append(f"{idx}. {result['title']}")
                        results.append(f"   {result['url']}")
                        results.append(f"   {result['content'][:300]}...")
                        results.append("")
                    
                    return "\n".join(results) if results else "No results found"
                else:
                    return f"Search failed: {response.status_code}"
        
        except Exception as e:
            return f"Error during search: {str(e)}"
    
    async def search_solution(self, error_message: str) -> str:
        """Search for solutions to an error"""
        # Extract key error parts
        error_type = error_message.split(':')[0] if ':' in error_message else error_message[:50]
        
        # Build search query
        query = f"python {error_type} solution fix"
        
        try:
            results = await self.search(query, max_results=3)
            
            formatted = [
                "SOLUTION SEARCH RESULTS:",
                f"Error: {error_type}",
                "",
                results
            ]
            
            return "\n".join(formatted)
        
        except Exception as e:
            return f"Error searching for solution: {str(e)}"
    
    async def search_code_example(self, task: str) -> str:
        """Search for code examples"""
        query = f"python code example {task}"
        return await self.search(query, max_results=3)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        return [
            {
                "name": "web_search",
                "description": "Search the web for information, solutions, or code examples",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "default": 5, "description": "Number of results"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_solution",
                "description": "Search for solutions to a specific error or problem",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "error_message": {"type": "string", "description": "Error message or problem description"}
                    },
                    "required": ["error_message"]
                }
            },
            {
                "name": "search_code_example",
                "description": "Search for code examples for a specific task",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"}
                    },
                    "required": ["task"]
                }
            }
        ]