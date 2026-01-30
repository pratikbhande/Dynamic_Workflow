from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str
    file_ids: Optional[List[str]] = None  # Override files for execution

class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str
    final_output: Any
    all_outputs: Optional[Dict[str, Any]] = None