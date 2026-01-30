from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..schemas.execution import ExecuteWorkflowRequest, ExecuteWorkflowResponse
from ...application.services.workflow_service import WorkflowService
from ...application.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])
workflow_service = WorkflowService()
execution_service = ExecutionService()


@router.post("/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest):
    """
    Execute a workflow with full file context
    
    The workflow must be in 'approved' status before execution.
    
    Execution process:
    1. Validates workflow structure
    2. Gathers all file context
    3. Executes agents in dependency order
    4. Passes real data between agents
    5. Returns final output
    
    Example:
```json
    {
        "workflow_id": "wf_abc123",
        "file_ids": ["file_xyz", "file_abc"]  // Optional: override files
    }
```
    """
    try:
        # Get workflow
        workflow = await workflow_service.get_workflow(request.workflow_id)
        
        # Check status
        if workflow.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Workflow must be approved before execution. Current status: {workflow.status}"
            )
        
        # Execute with full context
        result = await execution_service.execute_workflow(
            workflow=workflow,
            file_ids=request.file_ids
        )
        
        return ExecuteWorkflowResponse(
            execution_id=result["execution_id"],
            status=result["status"],
            final_output=result["final_output"],
            all_outputs=result.get("all_outputs")
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing workflow: {str(e)}"
        )


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    """
    Get execution details
    
    Returns:
    - Execution status
    - All agent outputs
    - Timing information
    - Error details if failed
    """
    try:
        execution = await execution_service.get_execution(execution_id)
        
        # Format response
        response = {
            "execution_id": execution["id"],
            "workflow_id": execution["workflow_id"],
            "status": execution["status"],
            "start_time": execution.get("start_time").isoformat() if execution.get("start_time") else None,
            "end_time": execution.get("end_time").isoformat() if execution.get("end_time") else None,
            "agent_outputs": execution.get("agent_outputs", {}),
            "provisioned_resources": execution.get("provisioned_resources", {})
        }
        
        # Calculate duration if completed
        if execution.get("start_time") and execution.get("end_time"):
            duration = (execution["end_time"] - execution["start_time"]).total_seconds()
            response["duration_seconds"] = duration
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/output/{agent_id}")
async def get_agent_output(execution_id: str, agent_id: str):
    """
    Get output from a specific agent in an execution
    
    Useful for debugging or retrieving intermediate results
    """
    try:
        execution = await execution_service.get_execution(execution_id)
        
        agent_outputs = execution.get("agent_outputs", {})
        
        if agent_id not in agent_outputs:
            raise ValueError(f"Agent {agent_id} not found in execution outputs")
        
        return {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "output": agent_outputs[agent_id]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """
    Cancel a running execution
    
    Note: This is a placeholder for future implementation.
    Currently, executions run to completion.
    """
    # TODO: Implement execution cancellation
    # This would require:
    # - Task queue integration
    # - Graceful agent shutdown
    # - Resource cleanup
    
    return {
        "message": "Execution cancellation not yet implemented",
        "execution_id": execution_id
    }


@router.get("/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    level: Optional[str] = Query(None, description="Filter by log level: info, warning, error")
):
    """
    Get execution logs
    
    Note: This is a placeholder for future implementation.
    Logs would include detailed agent execution steps.
    """
    # TODO: Implement logging system
    # This would require:
    # - Structured logging during execution
    # - Log storage (MongoDB or separate logging system)
    # - Log retrieval and filtering
    
    return {
        "message": "Execution logging not yet implemented",
        "execution_id": execution_id
    }


@router.get("/")
async def list_executions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """
    List all executions
    
    Query parameters:
    - status: Filter by execution status
    - limit: Maximum results to return
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Get executions
        cursor = db.get_collection("executions").find(query).sort(
            "start_time", -1
        ).limit(limit)
        
        executions = await cursor.to_list(length=limit)
        
        # Format response
        formatted = []
        for execution in executions:
            exec_data = {
                "execution_id": execution["id"],
                "workflow_id": execution["workflow_id"],
                "status": execution["status"],
                "start_time": execution.get("start_time").isoformat() if execution.get("start_time") else None,
                "end_time": execution.get("end_time").isoformat() if execution.get("end_time") else None
            }
            
            if execution.get("start_time") and execution.get("end_time"):
                duration = (execution["end_time"] - execution["start_time"]).total_seconds()
                exec_data["duration_seconds"] = duration
            
            formatted.append(exec_data)
        
        return {
            "total": len(formatted),
            "executions": formatted
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing executions: {str(e)}"
        )


@router.delete("/{execution_id}")
async def delete_execution(execution_id: str):
    """
    Delete an execution record
    
    Only completed or failed executions can be deleted.
    Running executions must be cancelled first.
    """
    try:
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        
        # Get execution
        execution = await db.get_collection("executions").find_one({"id": execution_id})
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        # Check if running
        if execution["status"] == "running":
            raise ValueError("Cannot delete running execution. Cancel it first.")
        
        # Delete
        await db.get_collection("executions").delete_one({"id": execution_id})
        
        return {
            "status": "success",
            "message": f"Execution {execution_id} deleted"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting execution: {str(e)}"
        )