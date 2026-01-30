from typing import Dict, List, Any
from ..vector_stores.factory import VectorStoreFactory, VectorDBType
from ..mcp.filesystem_mcp import FilesystemMCP
from ..mcp.mongodb_mcp import MongoDBMCP
from ..mcp.slack_mcp import SlackMCP
from ...domain.models import ToolRequirement
import uuid

class ToolRegistry:
    """Registry for all available tools and provisioning"""
    
    def __init__(self):
        self.vector_store_factory = VectorStoreFactory()
        self.mcp_clients = {
            "filesystem": FilesystemMCP(),
            "mongodb": MongoDBMCP(),
            "slack": SlackMCP()
        }
        
        self.available_tools = {
            "chromadb": {"type": "vector_db", "description": "Embedded vector database for semantic search"},
            "faiss": {"type": "vector_db", "description": "Fast in-memory vector search"},
            "filesystem": {"type": "mcp", "description": "File read/write operations"},
            "mongodb": {"type": "mcp", "description": "Database CRUD operations"},
            "slack": {"type": "mcp", "description": "Send Slack notifications"},
            "python_executor": {"type": "code_execution", "description": "Execute Python code"}
        }
    
    async def provision_tool(
        self,
        tool_name: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Provision a tool for an agent"""
        
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool {tool_name} not available")
        
        tool_info = self.available_tools[tool_name]
        
        if tool_info["type"] == "vector_db":
            return await self._provision_vector_db(tool_name, agent_id, purpose)
        elif tool_info["type"] == "mcp":
            return await self._provision_mcp(tool_name)
        elif tool_info["type"] == "code_execution":
            return {"type": "code_execution", "sandbox": True}
        
        return {}
    
    async def _provision_vector_db(
        self,
        db_type: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Create vector DB collection"""
        store = self.vector_store_factory.create(db_type)
        
        collection_name = await store.create_collection(
            name=f"{agent_id}_{purpose}",
            dimension=1536
        )
        
        return {
            "type": "vector_db",
            "db_type": db_type,
            "store": store,
            "collection_name": collection_name,
            "cleanup_required": True
        }
    
    async def _provision_mcp(self, mcp_name: str) -> Dict[str, Any]:
        """Get MCP client"""
        client = self.mcp_clients.get(mcp_name)
        if not client:
            return {"type": "mcp", "available": False}
        
        return {
            "type": "mcp",
            "mcp_name": mcp_name,
            "client": client,
            "available": client.connected
        }
    
    def get_tool_descriptions(self) -> str:
        """Get formatted list of available tools"""
        descriptions = []
        for name, info in self.available_tools.items():
            descriptions.append(f"- {name}: {info['description']}")
        return "\n".join(descriptions)
    
    async def cleanup_tools(self, provisioned_tools: List[Dict[str, Any]]) -> None:
        """Cleanup provisioned resources"""
        for tool in provisioned_tools:
            if tool.get("cleanup_required") and tool["type"] == "vector_db":
                store = tool["store"]
                collection_name = tool["collection_name"]
                await store.delete_collection(collection_name)
                print(f"✅ Cleaned up {tool['db_type']} collection: {collection_name}")