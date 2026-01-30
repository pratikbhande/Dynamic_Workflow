from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ToolType(str, Enum):
    VECTOR_DB = "vector_db"
    CODE_EXECUTION = "code_execution"
    MCP = "mcp"
    FILE_OPERATIONS = "file_operations"

class ToolRequirement(BaseModel):
    """Tool required by an agent"""
    name: str  # chromadb, faiss, filesystem, mongodb, slack, python_executor
    type: ToolType
    purpose: str
    config: Dict[str, Any] = {}

class AgentNode(BaseModel):
    """Individual agent in workflow"""
    id: str
    type: str  # data_processor, analyzer, rag_builder, code_executor
    name: str
    task: str
    detailed_prompt: str = ""
    required_tools: List[ToolRequirement] = []
    inputs: List[str] = []  # List of agent IDs or 'user_data'
    outputs: List[str] = []  # List of output keys
    
class Edge(BaseModel):
    """Connection between agents"""
    from_agent: str = Field(alias="from")
    to_agent: str = Field(alias="to")
    data_key: str  # What data is passed

class WorkflowGraph(BaseModel):
    """Complete workflow definition"""
    id: Optional[str] = None
    user_id: str
    name: str
    description: str
    agents: List[AgentNode]
    edges: List[Edge]
    status: str = "draft"  # draft, approved, executing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True

class ExecutionContext(BaseModel):
    """Runtime execution context"""
    workflow_id: str
    agent_outputs: Dict[str, Any] = {}  # agent_id -> output
    provisioned_resources: Dict[str, Any] = {}  # resource_name -> details
    status: str = "initializing"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
class DataInventory(BaseModel):
    """User's uploaded data"""
    files: List[Dict[str, Any]] = []
    databases: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}