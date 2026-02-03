"""Enhanced WebSearch Tool - Intelligent web research"""
from typing import Dict, Any, List, Optional
from ..base_tool import (
    BasePredefinedTool,
    ToolMetadata,
    CredentialRequirement,
    InputParameter,
    OutputSchema,
    ToolExecutionResult,
    ToolCategory
)


class WebSearchTool(BasePredefinedTool):
    """
    Web Search Tool - Intelligent web research
    
    Features:
    - Tavily API integration
    - Result ranking
    - Source filtering
    - Answer extraction
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="web_search",
            display_name="Web Search & Research",
            description="Search the web for current information, research topics, and find solutions",
            category=ToolCategory.WEB,
            tags=["web", "search", "research", "tavily"]
        )
    
    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="tavily_api_key",
                display_name="Tavily API Key",
                description="API key for Tavily web search (get free key at tavily.com)",
                required=True,
                secret=True
            )
        ]
    
    def get_input_parameters(self) -> List[InputParameter]:
        return [
            InputParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            ),
            InputParameter(
                name="max_results",
                type="number",
                description="Maximum number of results",
                required=False,
                default=5
            ),
            InputParameter(
                name="search_depth",
                type="string",
                description="Search depth",
                required=False,
                default="basic",
                options=["basic", "advanced"]
            ),
            InputParameter(
                name="include_domains",
                type="array",
                description="Domains to include (optional)",
                required=False
            ),
            InputParameter(
                name="exclude_domains",
                type="array",
                description="Domains to exclude (optional)",
                required=False
            )
        ]
    
    def get_output_schema(self) -> OutputSchema:
        return OutputSchema(
            type="object",
            description="Search results",
            properties={
                "query": "Original search query",
                "answer": "Direct answer if available",
                "results": "List of search results",
                "sources": "Source URLs"
            }
        )
    
    async def execute(
        self,
        inputs: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None
    ) -> ToolExecutionResult:
        """Execute web search"""
        
        try:
            query = inputs["query"]
            max_results = inputs.get("max_results", 5)
            search_depth = inputs.get("search_depth", "basic")
            include_domains = inputs.get("include_domains")
            exclude_domains = inputs.get("exclude_domains")
            
            print(f"\n🌐 Web Search Starting...")
            print(f"   Query: {query}")
            print(f"   Max Results: {max_results}")
            print(f"   Depth: {search_depth}")
            
            # Execute search
            import httpx
            
            async with httpx.AsyncClient() as client:
                payload = {
                    "api_key": credentials["tavily_api_key"],
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "include_raw_content": False
                }
                
                if include_domains:
                    payload["include_domains"] = include_domains
                if exclude_domains:
                    payload["exclude_domains"] = exclude_domains
                
                response = await client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Tavily API error: {response.status_code} - {response.text}")
                
                data = response.json()
            
            # Format results
            results = []
            for idx, result in enumerate(data.get("results", []), 1):
                results.append({
                    "rank": idx,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                })
            
            print(f"   ✅ Found {len(results)} results")
            
            return ToolExecutionResult(
                success=True,
                output={
                    "query": query,
                    "answer": data.get("answer"),
                    "results": results,
                    "sources": [r["url"] for r in results]
                },
                metadata={
                    "search_depth": search_depth,
                    "total_results": len(results)
                }
            )
            
        except Exception as e:
            import traceback
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Web search failed: {str(e)}\n{traceback.format_exc()}"
            )