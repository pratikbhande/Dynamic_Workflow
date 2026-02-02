from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class GenerateWorkflowRequest(BaseModel):
    task_description: str
    user_id: str = "default_user"
    file_ids: Optional[List[str]] = None  # None = all user files, [] = no files, ["file_x"] = specific files

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
    modification_prompt: Optional[str] = None

class WorkflowListResponse(BaseModel):
    workflows: List[Dict[str, Any]]