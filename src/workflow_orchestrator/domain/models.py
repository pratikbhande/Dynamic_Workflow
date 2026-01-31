from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ToolRequirement(BaseModel):
    """Tool requirement for an agent"""
    name: str
    type: str  # vector_db, code_execution, mcp
    purpose: str
    config: Dict[str, Any] = {}


class AgentNode(BaseModel):
    """Individual agent in the workflow"""
    id: str
    type: str
    name: str
    task: str
    detailed_prompt: str
    required_tools: List[ToolRequirement] = []
    inputs: List[str] = []
    outputs: List[str] = []
    output_format: Optional[str] = None


class Edge(BaseModel):
    """Edge connecting two agents"""
    # Accept both formats for compatibility
    from_agent: Optional[str] = Field(None, alias="from")
    to_agent: Optional[str] = Field(None, alias="to")
    data_key: str
    
    class Config:
        populate_by_name = True
    
    @property
    def from_(self) -> str:
        """Get from agent (handles both field names)"""
        return self.from_agent or ""
    
    @property
    def to_(self) -> str:
        """Get to agent (handles both field names)"""
        return self.to_agent or ""
    
    def model_dump(self, **kwargs):
        """Override to ensure consistent output"""
        data = super().model_dump(**kwargs)
        # Normalize to 'from' and 'to' for output
        if 'from_agent' in data:
            data['from'] = data.pop('from_agent')
        if 'to_agent' in data:
            data['to'] = data.pop('to_agent')
        return data


class WorkflowGraph(BaseModel):
    """Complete workflow graph"""
    id: str
    user_id: str
    name: str
    description: str
    agents: List[AgentNode]
    edges: List[Edge]
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionContext(BaseModel):
    """Runtime execution context"""
    workflow_id: str
    agent_outputs: Dict[str, Any] = {}
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None