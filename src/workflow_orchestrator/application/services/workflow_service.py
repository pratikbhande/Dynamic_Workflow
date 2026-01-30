from typing import Dict, Any, List
from ...domain.services.workflow_generator import WorkflowGenerator
from ...domain.models import WorkflowGraph
from ...infrastructure.database.mongodb import get_mongodb
from datetime import datetime
import uuid

class WorkflowService:
    """Application service for workflow operations"""
    
    def __init__(self):
        self.generator = WorkflowGenerator()
    
    async def generate_workflow(
        self,
        user_id: str,
        task_description: str,
        file_ids: List[str] = None  # NEW: Specific files to use
    ) -> WorkflowGraph:
        """Generate workflow from task description with file context"""
        
        print(f"\n🔄 Generating workflow for task: {task_description}")
        if file_ids:
            print(f"   Using files: {file_ids}")
        
        # Generate using OpenAI with full context
        workflow_dict = await self.generator.generate_workflow(
            task_description=task_description,
            user_id=user_id,
            file_ids=file_ids
        )
        
        # Create WorkflowGraph model
        workflow = WorkflowGraph(
            id=f"wf_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=workflow_dict["workflow_name"],
            description=workflow_dict["description"],
            agents=workflow_dict["agents"],
            edges=workflow_dict["edges"],
            status="draft"
        )
        
        # Save to database
        db = await get_mongodb()
        await db.get_collection("workflows").insert_one(workflow.model_dump())
        
        print(f"✅ Workflow generated: {workflow.id}")
        print(f"   Agents: {len(workflow.agents)}")
        
        return workflow
    
    async def get_workflow(self, workflow_id: str) -> WorkflowGraph:
        """Get workflow by ID"""
        db = await get_mongodb()
        workflow_dict = await db.get_collection("workflows").find_one({"id": workflow_id})
        
        if not workflow_dict:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        return WorkflowGraph(**workflow_dict)
    
    async def approve_workflow(self, workflow_id: str) -> WorkflowGraph:
        """Approve workflow for execution"""
        db = await get_mongodb()
        
        await db.get_collection("workflows").update_one(
            {"id": workflow_id},
            {"$set": {"status": "approved"}}
        )
        
        return await self.get_workflow(workflow_id)
    
    async def modify_workflow(
        self,
        workflow_id: str,
        modifications: str,
        user_id: str
    ) -> WorkflowGraph:
        """Modify workflow based on user feedback"""
        
        # Get existing workflow
        workflow = await self.get_workflow(workflow_id)
        
        # Use LLM to modify
        from ...domain.services.workflow_generator import WorkflowGenerator
        generator = WorkflowGenerator()
        
        # Get files from original workflow
        db = await get_mongodb()
        file_ids = []
        
        # Extract file IDs from agent prompts (simple extraction)
        for agent in workflow.agents:
            if "file_id" in agent.detailed_prompt:
                # Extract file IDs from prompt
                import re
                matches = re.findall(r'file_[a-z0-9]+', agent.detailed_prompt)
                file_ids.extend(matches)
        
        file_ids = list(set(file_ids))  # Unique
        
        # Regenerate with modifications
        modification_prompt = f"""
Original task: {workflow.description}

User feedback: {modifications}

Generate an updated workflow that addresses the user's feedback.
"""
        
        new_workflow_dict = await generator.generate_workflow(
            task_description=modification_prompt,
            user_id=user_id,
            file_ids=file_ids
        )
        
        # Update existing workflow
        await db.get_collection("workflows").update_one(
            {"id": workflow_id},
            {"$set": {
                "agents": new_workflow_dict["agents"],
                "edges": new_workflow_dict["edges"],
                "description": new_workflow_dict["description"],
                "status": "draft"
            }}
        )
        
        return await self.get_workflow(workflow_id)
    
    async def list_workflows(self, user_id: str) -> list:
        """List all workflows for a user"""
        db = await get_mongodb()
        cursor = db.get_collection("workflows").find({"user_id": user_id})
        workflows = await cursor.to_list(length=100)
        return workflows