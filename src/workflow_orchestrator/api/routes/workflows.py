from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..schemas.workflow import (
    GenerateWorkflowRequest,
    GenerateWorkflowResponse,
    ApproveWorkflowRequest,
    ModifyWorkflowRequest,
    WorkflowListResponse
)
from ...application.services.workflow_service import WorkflowService
from ...application.services.file_service import FileService

router = APIRouter(prefix="/workflows", tags=["workflows"])
workflow_service = WorkflowService()
file_service = FileService()


@router.post("/generate", response_model=GenerateWorkflowResponse)
async def generate_workflow(request: GenerateWorkflowRequest):
    """
    Generate a new workflow from task description with full file context
    
    This endpoint:
    1. Retrieves all uploaded files for the user (or specific files if file_ids provided)
    2. Extracts complete metadata (columns, sample data, content)
    3. Sends everything to GPT-4 to generate detailed agent prompts
    4. Returns workflow with executable, context-aware agent instructions
    
    Example:
```json
    {
        "task_description": "Analyze sales data and generate report",
        "user_id": "user_123",
        "file_ids": ["file_abc", "file_def"]  // Optional: specific files
    }
```
    """
    try:
        # Validate that files exist if file_ids provided
        if request.file_ids:
            for file_id in request.file_ids:
                try:
                    await file_service.get_file(file_id)
                except ValueError:
                    raise HTTPException(
                        status_code=404,
                        detail=f"File {file_id} not found"
                    )
        
        # Generate workflow with full context
        workflow = await workflow_service.generate_workflow(
            user_id=request.user_id,
            task_description=request.task_description,
            file_ids=request.file_ids
        )
        
        return GenerateWorkflowResponse(
            workflow_id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            agents=[agent.model_dump() for agent in workflow.agents],
            edges=[edge.model_dump() for edge in workflow.edges],
            status=workflow.status
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating workflow: {str(e)}"
        )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Get complete workflow details including all agent prompts
    
    Returns:
    - Workflow metadata
    - All agents with detailed prompts
    - Dependencies (edges)
    - Status
    
    Use this to review the workflow before approval
    """
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        
        # Format for better readability
        response = {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat(),
            "user_id": workflow.user_id,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "type": agent.type,
                    "task": agent.task,
                    "detailed_prompt": agent.detailed_prompt,
                    "required_tools": [
                        {
                            "name": tool.name,
                            "type": tool.type,
                            "purpose": tool.purpose
                        }
                        for tool in agent.required_tools
                    ],
                    "inputs": agent.inputs,
                    "outputs": agent.outputs
                }
                for agent in workflow.agents
            ],
            "edges": [
                {
                    "from": edge.from_agent,
                    "to": edge.to_agent,
                    "data_key": edge.data_key
                }
                for edge in workflow.edges
            ]
        }
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve")
async def approve_workflow(request: ApproveWorkflowRequest):
    """
    Approve a workflow for execution
    
    Once approved, the workflow can be executed.
    Status changes from 'draft' to 'approved'
    """
    try:
        workflow = await workflow_service.approve_workflow(request.workflow_id)
        
        return {
            "status": "success",
            "workflow_id": workflow.id,
            "workflow_status": workflow.status,
            "message": f"Workflow '{workflow.name}' approved and ready for execution"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modify")
async def modify_workflow(request: ModifyWorkflowRequest):
    """
    Modify workflow based on user feedback
    
    Regenerates the workflow with user's requested changes.
    The workflow status resets to 'draft' and needs re-approval.
    
    Example:
```json
    {
        "workflow_id": "wf_abc123",
        "modifications": "Add a step to generate charts and save as PNG files",
        "user_id": "user_123"
    }
```
    """
    try:
        workflow = await workflow_service.modify_workflow(
            workflow_id=request.workflow_id,
            modifications=request.modifications,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "workflow_id": workflow.id,
            "workflow_status": workflow.status,
            "message": "Workflow modified successfully. Please review and approve again.",
            "agents_count": len(workflow.agents),
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "type": agent.type,
                    "task": agent.task
                }
                for agent in workflow.agents
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error modifying workflow: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=WorkflowListResponse)
async def list_workflows(
    user_id: str,
    status: Optional[str] = Query(None, description="Filter by status: draft, approved, executing, completed, failed"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of workflows to return")
):
    """
    List all workflows for a user
    
    Query parameters:
    - status: Filter by workflow status
    - limit: Maximum results (default 50, max 100)
    
    Returns summary of workflows with basic info
    """
    try:
        workflows = await workflow_service.list_workflows(user_id)
        
        # Filter by status if provided
        if status:
            workflows = [w for w in workflows if w.get("status") == status]
        
        # Limit results
        workflows = workflows[:limit]
        
        # Format response
        formatted_workflows = [
            {
                "workflow_id": w["id"],
                "name": w["name"],
                "description": w["description"],
                "status": w["status"],
                "created_at": w["created_at"].isoformat() if "created_at" in w else None,
                "agents_count": len(w.get("agents", []))
            }
            for w in workflows
        ]
        
        return WorkflowListResponse(workflows=formatted_workflows)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing workflows: {str(e)}"
        )


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow
    
    Permanently deletes the workflow and all its data.
    Cannot be undone.
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        
        # Check if workflow exists
        workflow = await db.get_collection("workflows").find_one({"id": workflow_id})
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Delete workflow
        await db.get_collection("workflows").delete_one({"id": workflow_id})
        
        # Also delete any executions of this workflow
        await db.get_collection("executions").delete_many({"workflow_id": workflow_id})
        
        return {
            "status": "success",
            "message": f"Workflow {workflow_id} deleted successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting workflow: {str(e)}"
        )


@router.get("/{workflow_id}/executions")
async def get_workflow_executions(
    workflow_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of executions to return")
):
    """
    Get all executions of a specific workflow
    
    Returns execution history with status and timestamps
    Useful for tracking workflow performance over time
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        
        # Verify workflow exists
        workflow = await db.get_collection("workflows").find_one({"id": workflow_id})
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Get executions
        cursor = db.get_collection("executions").find(
            {"workflow_id": workflow_id}
        ).sort("start_time", -1).limit(limit)
        
        executions = await cursor.to_list(length=limit)
        
        # Format response
        formatted_executions = []
        for execution in executions:
            exec_data = {
                "execution_id": execution["id"],
                "workflow_id": execution["workflow_id"],
                "status": execution["status"],
                "start_time": execution["start_time"].isoformat() if execution.get("start_time") else None,
                "end_time": execution["end_time"].isoformat() if execution.get("end_time") else None
            }
            
            # Calculate duration if completed
            if execution.get("start_time") and execution.get("end_time"):
                duration = (execution["end_time"] - execution["start_time"]).total_seconds()
                exec_data["duration_seconds"] = duration
            
            formatted_executions.append(exec_data)
        
        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow["name"],
            "total_executions": len(formatted_executions),
            "executions": formatted_executions
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving executions: {str(e)}"
        )


@router.post("/{workflow_id}/duplicate")
async def duplicate_workflow(
    workflow_id: str,
    new_name: Optional[str] = None
):
    """
    Duplicate an existing workflow
    
    Creates a copy of the workflow with a new ID.
    Useful for creating variations or templates.
    
    Query parameters:
    - new_name: Optional new name for the duplicated workflow
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        import uuid
        
        db = await get_mongodb()
        
        # Get original workflow
        original = await db.get_collection("workflows").find_one({"id": workflow_id})
        if not original:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Create duplicate
        duplicate = original.copy()
        duplicate["id"] = f"wf_{uuid.uuid4().hex[:12]}"
        duplicate["name"] = new_name if new_name else f"{original['name']} (Copy)"
        duplicate["status"] = "draft"
        duplicate["created_at"] = datetime.utcnow()
        
        # Remove MongoDB _id
        if "_id" in duplicate:
            del duplicate["_id"]
        
        # Insert duplicate
        await db.get_collection("workflows").insert_one(duplicate)
        
        return {
            "status": "success",
            "original_workflow_id": workflow_id,
            "new_workflow_id": duplicate["id"],
            "new_workflow_name": duplicate["name"],
            "message": "Workflow duplicated successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error duplicating workflow: {str(e)}"
        )


@router.get("/{workflow_id}/export")
async def export_workflow(workflow_id: str):
    """
    Export workflow as JSON
    
    Returns the complete workflow definition that can be:
    - Saved as a file
    - Shared with others
    - Imported into another system
    - Used as a template
    """
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "workflow": {
                "name": workflow.name,
                "description": workflow.description,
                "agents": [agent.model_dump() for agent in workflow.agents],
                "edges": [edge.model_dump() for edge in workflow.edges]
            }
        }
        
        return export_data
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting workflow: {str(e)}"
        )


@router.post("/import")
async def import_workflow(
    workflow_data: dict,
    user_id: str = "default_user"
):
    """
    Import a workflow from exported JSON
    
    Creates a new workflow from exported data.
    Validates the structure before importing.
    
    Request body should be the exported JSON from /export endpoint
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        from ...domain.models import WorkflowGraph
        import uuid
        
        # Validate structure
        if "workflow" not in workflow_data:
            raise ValueError("Invalid workflow data: missing 'workflow' key")
        
        wf_data = workflow_data["workflow"]
        required_keys = ["name", "description", "agents", "edges"]
        missing = [k for k in required_keys if k not in wf_data]
        if missing:
            raise ValueError(f"Invalid workflow data: missing keys {missing}")
        
        # Create new workflow
        workflow = WorkflowGraph(
            id=f"wf_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=wf_data["name"],
            description=wf_data["description"],
            agents=wf_data["agents"],
            edges=wf_data["edges"],
            status="draft"
        )
        
        # Save to database
        db = await get_mongodb()
        await db.get_collection("workflows").insert_one(workflow.model_dump())
        
        return {
            "status": "success",
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "message": "Workflow imported successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing workflow: {str(e)}"
        )


@router.get("/{workflow_id}/validate")
async def validate_workflow(workflow_id: str):
    """
    Validate workflow structure
    
    Checks for:
    - Circular dependencies
    - Missing agent references
    - Invalid tool configurations
    - Proper data flow
    
    Returns validation results with errors and warnings
    """
    try:
        from ...domain.services.dependency_resolver import DependencyResolver
        
        workflow = await workflow_service.get_workflow(workflow_id)
        resolver = DependencyResolver()
        
        # Validate
        validation = resolver.validate_workflow(
            agents=[agent.model_dump() for agent in workflow.agents],
            edges=[edge.model_dump() for edge in workflow.edges]
        )
        
        # Get execution order if valid
        execution_order = None
        if validation["valid"]:
            try:
                levels = resolver.topological_sort(
                    agents=[agent.model_dump() for agent in workflow.agents],
                    edges=[edge.model_dump() for edge in workflow.edges]
                )
                
                # Format execution order
                execution_order = []
                for i, level in enumerate(levels, 1):
                    agent_names = [
                        agent.name for agent in workflow.agents
                        if agent.id in level
                    ]
                    execution_order.append({
                        "level": i,
                        "agents": agent_names,
                        "parallel": len(agent_names) > 1
                    })
            except Exception as e:
                validation["warnings"].append(f"Could not determine execution order: {str(e)}")
        
        response = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "execution_order": execution_order
        }
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating workflow: {str(e)}"
        )


@router.get("/{workflow_id}/estimate-cost")
async def estimate_workflow_cost(workflow_id: str):
    """
    Estimate execution cost for workflow
    
    Provides rough cost estimates based on:
    - Number of agents
    - Model complexity
    - Expected token usage
    - Tool usage (vector DBs, etc.)
    
    Note: Actual costs may vary based on execution
    """
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        
        # Simple cost estimation
        # This is a rough estimate - actual costs depend on execution
        base_cost_per_agent = {
            "data_processor": 0.05,  # Assuming Haiku/Sonnet
            "rag_builder": 0.10,      # Vector DB operations + LLM
            "analyzer": 0.08,
            "report_generator": 0.06,
            "code_executor": 0.03
        }
        
        total_estimated_cost = 0
        agent_costs = []
        
        for agent in workflow.agents:
            agent_type = agent.type
            base_cost = base_cost_per_agent.get(agent_type, 0.05)
            
            # Adjust based on tools
            tool_multiplier = 1.0
            for tool in agent.required_tools:
                if tool.type == "vector_db":
                    tool_multiplier *= 1.5  # Vector DB adds cost
                elif tool.type == "code_execution":
                    tool_multiplier *= 1.2
            
            agent_cost = base_cost * tool_multiplier
            total_estimated_cost += agent_cost
            
            agent_costs.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "estimated_cost": round(agent_cost, 4)
            })
        
        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "total_agents": len(workflow.agents),
            "estimated_total_cost": round(total_estimated_cost, 4),
            "currency": "USD",
            "agent_breakdown": agent_costs,
            "note": "This is a rough estimate. Actual costs depend on data size, complexity, and execution time."
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating cost: {str(e)}"
        )


# Add datetime import at top of file
from datetime import datetime