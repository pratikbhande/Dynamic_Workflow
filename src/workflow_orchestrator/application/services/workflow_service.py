from typing import Dict, Any, List
from ...domain.services.workflow_generator import WorkflowGenerator
from ...domain.models import WorkflowGraph, AgentNode, Edge, ToolRequirement
from ...domain.services.workflow_memory import WorkflowMemory
from ...infrastructure.database.mongodb import get_mongodb
from datetime import datetime
from ...config import settings
import uuid

class WorkflowService:
    """Application service for workflow operations"""
    
    def __init__(self):
        self.generator = WorkflowGenerator()
        self.workflow_memory = WorkflowMemory()
    
    async def generate_workflow(
        self,
        user_id: str,
        task_description: str,
        file_ids: List[str] = None
    ) -> WorkflowGraph:
        """Generate workflow from task description with intelligent reuse"""
        
        print(f"\n📋 Generating workflow for task: {task_description}")
        if file_ids:
            print(f"   Using files: {file_ids}")
        
        # CHECK MEMORY FIRST
        if settings.ENABLE_WORKFLOW_MEMORY:
            print(f"\n🔍 Checking workflow memory for similar tasks...")
            similar_workflow = await self.workflow_memory.find_similar_workflow(
                task_description=task_description,
                user_id=user_id
            )
            
            if similar_workflow:
                # Remove MongoDB _id
                if '_id' in similar_workflow:
                    del similar_workflow['_id']
                
                # Create new workflow ID but reuse structure
                # import uuid
                new_workflow = similar_workflow.copy()
                new_workflow['id'] = f"wf_{uuid.uuid4().hex[:12]}"
                new_workflow['status'] = 'draft'
                new_workflow['created_at'] = datetime.utcnow()
                
                # Save reused workflow
                db = await get_mongodb()
                await db.get_collection("workflows").insert_one(new_workflow)
                
                print(f"♻️  Reused workflow: {similar_workflow['name']}")
                
                return WorkflowGraph(**new_workflow)
        
        # Generate new workflow if no match found
        print(f"\n🆕 Generating new workflow...")
        workflow_dict = await self.generator.generate_workflow(
            task_description=task_description,
            user_id=user_id,
            file_ids=file_ids
        )
        
        # Normalize edges format
        normalized_edges = []
        for edge in workflow_dict.get("edges", []):
            normalized_edge = {
                "from_agent": edge.get("from_agent") or edge.get("from"),
                "to_agent": edge.get("to_agent") or edge.get("to"),
                "data_key": edge.get("data_key", "output")
            }
            normalized_edges.append(normalized_edge)
        
        # Create WorkflowGraph model
        workflow = WorkflowGraph(
            id=f"wf_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=workflow_dict["workflow_name"],
            description=workflow_dict["description"],
            agents=[AgentNode(**agent) for agent in workflow_dict["agents"]],
            edges=[Edge(**edge) for edge in normalized_edges],
            status="draft"
        )

        # VALIDATION: Ensure required_tools are present
        print(f"\n🔍 Validating workflow tools...")
        for agent in workflow.agents:
            if not agent.required_tools:
                print(f"   ⚠️  {agent.name} has NO required_tools! Fixing...")
                
                # Auto-fix based on agent type
                if agent.type == 'rag_builder':
                    agent.required_tools = [
                        ToolRequirement(name="chromadb", type="vector_db", purpose="index documents"),
                        ToolRequirement(name="python_executor", type="code_execution", purpose="process files")
                    ]
                elif agent.type == 'chat_endpoint_builder':
                    agent.required_tools = [
                        ToolRequirement(name="python_executor", type="code_execution", purpose="create endpoint")
                    ]
                else:
                    agent.required_tools = [
                        ToolRequirement(name="python_executor", type="code_execution", purpose="execute task")
                    ]
                
                print(f"   ✅ Added {len(agent.required_tools)} tools to {agent.name}")
            else:
                print(f"   ✅ {agent.name} has {len(agent.required_tools)} tools")

        print(f"✅ Validation complete\n")
        
        # Save to database
        db = await get_mongodb()
        workflow_data = workflow.model_dump()
        
        # Ensure edges are in correct format for storage
        workflow_data["edges"] = [
            {
                "from_agent": edge.from_agent,
                "to_agent": edge.to_agent,
                "data_key": edge.data_key
            }
            for edge in workflow.edges
        ]
        
        await db.get_collection("workflows").insert_one(workflow_data)
        
        # STORE IN MEMORY for future reuse
        if settings.ENABLE_WORKFLOW_MEMORY:
            await self.workflow_memory.store_workflow(
                workflow=workflow_data,
                task_description=task_description
            )
        
        print(f"✅ Workflow generated: {workflow.id}")
        print(f"   Agents: {len(workflow.agents)}")
        
        return workflow
    
    async def get_workflow(self, workflow_id: str) -> WorkflowGraph:
        """Get workflow by ID"""
        db = await get_mongodb()
        workflow_dict = await db.get_collection("workflows").find_one({"id": workflow_id})
        
        if not workflow_dict:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # Remove MongoDB _id
        if '_id' in workflow_dict:
            del workflow_dict['_id']
        
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
        
        workflow = await self.get_workflow(workflow_id)
        
        # Get files from original workflow
        db = await get_mongodb()
        file_ids = []
        
        # Extract file IDs from agent prompts
        for agent in workflow.agents:
            if "file_id" in agent.detailed_prompt:
                import re
                matches = re.findall(r'file_[a-z0-9]+', agent.detailed_prompt)
                file_ids.extend(matches)
        
        file_ids = list(set(file_ids))
        
        # Regenerate with modifications
        modification_prompt = f"""
Original task: {workflow.description}

User feedback: {modifications}

Generate an updated workflow that addresses the user's feedback.
"""
        
        new_workflow_dict = await self.generator.generate_workflow(
            task_description=modification_prompt,
            user_id=user_id,
            file_ids=file_ids
        )
        
        # Normalize edges
        normalized_edges = []
        for edge in new_workflow_dict.get("edges", []):
            normalized_edge = {
                "from_agent": edge.get("from_agent") or edge.get("from"),
                "to_agent": edge.get("to_agent") or edge.get("to"),
                "data_key": edge.get("data_key", "output")
            }
            normalized_edges.append(normalized_edge)
        
        # Update existing workflow
        await db.get_collection("workflows").update_one(
            {"id": workflow_id},
            {"$set": {
                "agents": new_workflow_dict["agents"],
                "edges": normalized_edges,
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
        
        # Remove MongoDB _id from all workflows
        for wf in workflows:
            if '_id' in wf:
                del wf['_id']
        
        return workflows