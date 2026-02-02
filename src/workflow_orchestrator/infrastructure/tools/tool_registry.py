from typing import Dict, List, Any
import re
from ..vector_stores.factory import VectorStoreFactory, VectorDBType
from ..mcp.filesystem_mcp import FilesystemMCP
from ..mcp.mongodb_mcp import MongoDBMCP
from ..mcp.slack_mcp import SlackMCP
from ..mcp.websearch_mcp import WebSearchMCP
from ...domain.models import ToolRequirement
import uuid

class ToolRegistry:
    """Registry for all available tools and provisioning"""
    
    def __init__(self):
        self.vector_store_factory = VectorStoreFactory()
        self.mcp_clients = {
            "filesystem": FilesystemMCP(),
            "mongodb": MongoDBMCP(),
            "slack": SlackMCP(),
            "websearch": WebSearchMCP()
        }
        
        self.available_tools = {
            "chromadb": {"type": "vector_db", "description": "Embedded vector database for semantic search"},
            "faiss": {"type": "vector_db", "description": "Fast in-memory vector search"},
            "filesystem": {"type": "mcp", "description": "File read/write operations"},
            "mongodb": {"type": "mcp", "description": "Database CRUD operations"},
            "slack": {"type": "mcp", "description": "Send Slack notifications"},
            "websearch": {"type": "mcp", "description": "Search web for solutions and information"},
            "python_executor": {"type": "code_execution", "description": "Execute Python code"}
        }
    
    def _sanitize_collection_name(self, name: str) -> str:
        """
        Sanitize collection name for ChromaDB requirements:
        - 3-63 characters (reduced from 512 for safety)
        - Only [a-zA-Z0-9._-]
        - Must start and end with alphanumeric
        """
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        
        # Remove leading/trailing non-alphanumeric
        sanitized = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', sanitized)
        
        # Collapse multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Ensure it starts with alphanumeric
        if not sanitized or not sanitized[0].isalnum():
            sanitized = 'col_' + sanitized
        
        # Truncate to 63 chars max
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
        
        # Ensure minimum 3 chars
        if len(sanitized) < 3:
            sanitized = sanitized + '_db'
        
        return sanitized
    
    async def provision_tool(
        self,
        tool_name: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Provision a tool for an agent"""
        
        if tool_name not in self.available_tools:
            # Check if it's a service deployment tool (special case)
            if tool_name in ['deploy_streamlit', 'deploy_gradio']:
                return {
                    "type": "service_deployment",
                    "tool_name": tool_name,
                    "available": True
                }
            raise ValueError(f"Tool {tool_name} not available")
        
        tool_info = self.available_tools[tool_name]
        
        if tool_info["type"] == "vector_db":
            return await self._provision_vector_db(tool_name, agent_id, purpose)
        elif tool_info["type"] == "mcp":
            return await self._provision_mcp(tool_name)
        elif tool_info["type"] == "code_execution":
            return {"type": "code_execution", "sandbox": True}
        elif tool_info["type"] == "service_deployment":
            return {
                "type": "service_deployment",
                "tool_name": tool_name,
                "available": True
            }
        
        return {}
    
    async def _provision_vector_db(
        self,
        db_type: str,
        agent_id: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Create vector DB collection with sanitized name"""
        store = self.vector_store_factory.create(db_type)
        
        # Create base name and sanitize
        base_name = f"{agent_id}_{purpose}"
        sanitized_name = self._sanitize_collection_name(base_name)
        
        # Add random suffix for uniqueness
        collection_name = f"{sanitized_name}_{uuid.uuid4().hex[:8]}"
        
        # Final sanitization
        collection_name = self._sanitize_collection_name(collection_name)
        
        print(f"     📦 Creating collection: {collection_name}")
        
        collection_name = await store.create_collection(
            name=collection_name,
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