from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class GenerateWorkflowRequest(BaseModel):
    task_description: str
    user_id: str = "default_user"
    file_ids: Optional[List[str]] = None  # Specific files to use

class GenerateWorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    description: str
    agents: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    status: str

class ModifyWorkflowRequest(BaseModel):
    workflow_id: str
    modifications: str
    user_id: str = "default_user"

class ApproveWorkflowRequest(BaseModel):
    workflow_id: str

class WorkflowListResponse(BaseModel):
    workflows: List[Dict[str, Any]]