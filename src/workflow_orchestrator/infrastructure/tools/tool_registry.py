"""Tool Registry - Manages both predefined and dynamic tools"""
from typing import Dict, List, Any, Optional
import re
from ..vector_stores.factory import VectorStoreFactory, VectorDBType
from ..mcp.filesystem_mcp import FilesystemMCP
from ..mcp.mongodb_mcp import MongoDBMCP
from ..mcp.slack_mcp import SlackMCP
from ..mcp.websearch_mcp import WebSearchMCP
import uuid


class ToolRegistry:
    """
    Registry for all available tools
    
    Architecture:
    1. Predefined tools (imported from predefined/)
    2. Dynamic tools (provisioned on demand)
    3. MCP tools (external services)
    """
    
    def __init__(self):
        self.vector_store_factory = VectorStoreFactory()
        self.mcp_clients = {
            "filesystem": FilesystemMCP(),
            "mongodb": MongoDBMCP(),
            "slack": SlackMCP(),
            "websearch": WebSearchMCP()
        }
        self.predefined_tools = self._load_predefined_tools()
    
    def _load_predefined_tools(self) -> Dict[str, Any]:
        """Load predefined tools"""
        
        predefined = {}
        
        try:
            from .predefined import (
                RagBuilderTool,
                RagChatTool,
                ReportGeneratorTool,
                WebSearchTool
            )
            
            predefined["rag_builder"] = RagBuilderTool()
            predefined["rag_chat"] = RagChatTool()
            predefined["report_generator"] = ReportGeneratorTool()
            predefined["web_search"] = WebSearchTool()
            
            print(f"📦 Loaded {len(predefined)} predefined tools")
            
        except Exception as e:
            print(f"⚠️  Error loading predefined tools: {e}")
        
        return predefined
    
    def get_predefined_tool(self, tool_name: str):
        """Get predefined tool instance"""
        return self.predefined_tools.get(tool_name.lower())
    
    def list_predefined_tools(self) -> List[str]:
        """List available predefined tools"""
        return list(self.predefined_tools.keys())
    
    async def provision_tool(
        self,
        tool_name: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """
        Provision tool - checks predefined first, then dynamic
        
        Strategy:
        1. Check if predefined tool exists
        2. If not, provision dynamically
        3. Normalize tool names for matching
        """
        
        # Normalize name
        normalized = tool_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        
        print(f"     🔧 Provisioning '{tool_name}'")
        
        # Check predefined tools first
        if tool_name.lower() in self.predefined_tools:
            return {
                "type": "predefined",
                "tool_name": tool_name.lower()
            }
        
        # Check code execution keywords
        code_keywords = [
            "python", "executor", "code", "execute",
            "script", "processor", "parser"
        ]
        if any(keyword in normalized for keyword in code_keywords):
            return {
                "type": "code_execution",
                "tool_name": "python_executor",
                "sandbox": True
            }
        
        # Check vector DB keywords
        vector_keywords = ["vector", "chroma", "faiss", "rag", "index", "semantic"]
        if any(keyword in normalized for keyword in vector_keywords):
            return await self._provision_vector_db("chromadb", agent_id, purpose)
        
        # Check MCP keywords
        if "filesystem" in normalized or "file" in normalized:
            return await self._provision_mcp("filesystem")
        if "mongo" in normalized:
            return await self._provision_mcp("mongodb")
        if "slack" in normalized:
            return await self._provision_mcp("slack")
        if "web" in normalized or "search" in normalized:
            return await self._provision_mcp("websearch")
        
        # Default to code execution
        print(f"     ⚠️  Unknown tool '{tool_name}' → defaulting to code_execution")
        return {
            "type": "code_execution",
            "tool_name": "python_executor",
            "sandbox": True
        }
    
    async def _provision_vector_db(
        self,
        db_type: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Provision vector database"""
        store = self.vector_store_factory.create(db_type)
        
        collection_name = "rag_documents"
        
        try:
            await store.create_collection(name=collection_name, dimension=1536)
        except:
            pass  # Already exists
        
        return {
            "type": "vector_db",
            "db_type": db_type,
            "store": store,
            "collection_name": collection_name,
            "cleanup_required": False
        }
    
    async def _provision_mcp(self, mcp_name: str) -> Dict[str, Any]:
        """Get MCP client"""
        client = self.mcp_clients.get(mcp_name)
        return {
            "type": "mcp",
            "mcp_name": mcp_name,
            "client": client,
            "available": client.connected if client else False
        }
    
    async def cleanup_tools(self, provisioned_tools: List[Dict[str, Any]]) -> None:
        """Cleanup provisioned tools"""
        pass  # Implement if needed