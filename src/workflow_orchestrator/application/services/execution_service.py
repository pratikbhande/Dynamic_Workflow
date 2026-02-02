from typing import Dict, Any, List
from ...domain.models import WorkflowGraph, ExecutionContext
from ...domain.services.dependency_resolver import DependencyResolver
from ...infrastructure.agents.agent_executor import DynamicAgentExecutor
from ...infrastructure.database.mongodb import get_mongodb
from datetime import datetime
from ...config import settings
import uuid
import asyncio
import json

class ExecutionService:
    """Service for executing workflows with full file context and error memory"""
    
    def __init__(self):
        self.agent_executor = DynamicAgentExecutor()
        self.dependency_resolver = DependencyResolver()
    
    async def execute_workflow(
        self,
        workflow: WorkflowGraph,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Execute workflow with complete file context, self-healing, and service deployment"""
        
        print(f"\n{'='*80}")
        print(f"🚀 EXECUTING WORKFLOW: {workflow.name}")
        print(f"{'='*80}\n")
        
        # Validate workflow
        validation = self.dependency_resolver.validate_workflow(
            agents=[agent.model_dump() for agent in workflow.agents],
            edges=[edge.model_dump() for edge in workflow.edges]
        )
        
        if not validation["valid"]:
            raise ValueError(f"Invalid workflow: {validation['errors']}")
        
        # Gather file context
        files_context = await self._gather_files_context(workflow.user_id, file_ids)
        
        # Create execution context with error memory
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        context = ExecutionContext(
            workflow_id=workflow.id,
            agent_outputs={},
            status="running",
            start_time=datetime.utcnow()
        )
        
        # Initialize with file context and tracking
        context.agent_outputs["files_context"] = files_context
        context.agent_outputs["user_files"] = files_context["files"]
        context.agent_outputs["error_memory"] = {}
        context.agent_outputs["deployed_services"] = []  # Track deployed services
        
        # Save initial execution state
        db = await get_mongodb()
        await db.get_collection("executions").insert_one({
            "id": execution_id,
            **context.model_dump()
        })
        
        # Get execution order
        execution_levels = self.dependency_resolver.topological_sort(
            agents=[agent.model_dump() for agent in workflow.agents],
            edges=[edge.model_dump() for edge in workflow.edges]
        )
        
        print(f"📊 Execution Plan:")
        for i, level in enumerate(execution_levels):
            agents_in_level = [a.name for a in workflow.agents if a.id in level]
            print(f"  Level {i+1}: {', '.join(agents_in_level)}")
        print()
        
        # Execute level by level
        for level_num, agent_ids in enumerate(execution_levels, 1):
            print(f"\n{'='*60}")
            print(f"🎯 Executing Level {level_num}")
            print(f"{'='*60}\n")
            
            agents_in_level = [a for a in workflow.agents if a.id in agent_ids]
            
            # Execute agents in parallel
            tasks = []
            for agent in agents_in_level:
                # Build complete input with file context and error memory
                input_data = self._build_agent_input(
                    agent,
                    context.agent_outputs,
                    files_context
                )
                
                # USE RETRY VERSION
                task = self.agent_executor.execute_agent_with_retry(
                    agent_config=agent.model_dump(),
                    input_data=input_data,
                    max_retries=settings.MAX_RETRY_ATTEMPTS
                )
                tasks.append(task)
            
            # Wait for all agents
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store outputs and learn from errors
            for agent, result in zip(agents_in_level, results):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    context.agent_outputs[agent.id] = {
                        "error": error_msg,
                        "status": "failed"
                    }
                    context.status = "failed"
                    
                    # Store error in memory
                    error_sig = self._get_error_signature(error_msg)
                    context.agent_outputs["error_memory"][error_sig] = {
                        "error": error_msg,
                        "agent": agent.name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    # Parse output
                    output = result["output"]
                    try:
                        parsed_output = json.loads(output) if isinstance(output, str) and output.startswith('{') else output
                        context.agent_outputs[agent.id] = parsed_output
                    except:
                        context.agent_outputs[agent.id] = output
                    
                    # Check if service was deployed
                    if isinstance(output, str) and "deployed successfully" in output.lower():
                        # Extract service URL
                        import re
                        url_match = re.search(r'URL: (http://[^\s]+)', output)
                        if url_match:
                            context.agent_outputs["deployed_services"].append({
                                "agent": agent.name,
                                "url": url_match.group(1),
                                "type": "streamlit" if "streamlit" in output.lower() else "gradio"
                            })
                
                # Update execution in DB
                await db.get_collection("executions").update_one(
                    {"id": execution_id},
                    {"$set": {
                        "agent_outputs": context.agent_outputs,
                        "status": context.status
                    }}
                )
        
        # Mark complete
        if context.status != "failed":
            context.status = "completed"
        
        context.end_time = datetime.utcnow()
        
        await db.get_collection("executions").update_one(
            {"id": execution_id},
            {"$set": {
                "status": context.status,
                "end_time": context.end_time
            }}
        )
        
        # Get final output
        final_agent_id = workflow.agents[-1].id
        final_output = context.agent_outputs.get(final_agent_id, "No output")
        
        # Add deployed services to final output if any
        if context.agent_outputs.get("deployed_services"):
            final_output = {
                "result": final_output,
                "deployed_services": context.agent_outputs["deployed_services"]
            }
        
        print(f"\n{'='*80}")
        print(f"✅ WORKFLOW {context.status.upper()}")
        if context.agent_outputs.get("deployed_services"):
            print(f"\n🚀 DEPLOYED SERVICES:")
            for service in context.agent_outputs["deployed_services"]:
                print(f"   {service['type']}: {service['url']}")
        print(f"{'='*80}\n")
        
        return {
            "execution_id": execution_id,
            "status": context.status,
            "final_output": final_output,
            "all_outputs": context.agent_outputs
        }
    
    def _get_error_signature(self, error_msg: str) -> str:
        """Extract error signature for memory lookup"""
        # Extract key parts of error message
        if "KeyError" in error_msg:
            return "KeyError_missing_columns"
        elif "AttributeError" in error_msg and "applymap" in error_msg:
            return "AttributeError_applymap_deprecated"
        elif "not in index" in error_msg:
            return "KeyError_column_not_found"
        elif "trailing space" in error_msg.lower():
            return "ValueError_trailing_spaces"
        else:
            # Generic signature
            return error_msg.split('\n')[0][:50]
    
    async def _gather_files_context(
        self,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Gather complete file context for execution"""
        
        db = await get_mongodb()
        files_data = []
        
        if file_ids:
            for file_id in file_ids:
                file_record = await db.get_collection("files").find_one({"id": file_id})
                if file_record:
                    files_data.append(self._format_file_context(file_record))
        else:
            # Get all user files
            cursor = db.get_collection("files").find({"user_id": user_id})
            all_files = await cursor.to_list(length=50)
            for file_record in all_files:
                files_data.append(self._format_file_context(file_record))
        
        return {
            "files": files_data,
            "total_files": len(files_data)
        }
    
    def _format_file_context(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format file record for agent context"""
        
        context = {
            "file_id": file_record["id"],
            "filename": file_record["original_filename"],
            "type": file_record["file_type"],
            "path": file_record["file_path"],
            "full_text": file_record["text_content"]
        }
        
        # Add structured data for Excel/CSV
        if file_record["file_type"] in ['.xlsx', '.xls', '.csv']:
            processed = file_record["processed_data"]
            if 'sheets' in processed:
                context["sheets"] = processed["sheets"]
            elif 'data' in processed:
                context["data"] = processed["data"]
        
        return context
    
    def _build_agent_input(
        self,
        agent: Any,
        outputs: Dict[str, Any],
        files_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build complete input for agent including files, previous outputs, and error memory"""
        
        agent_input = {
            "files": files_context["files"],
            "task": agent.task
        }
        
        # Add error memory guidance
        error_memory = outputs.get("error_memory", {})
        if error_memory:
            error_guidance = "\n\nKNOWN ERROR PATTERNS (avoid these):\n"
            for sig, info in error_memory.items():
                error_guidance += f"- {sig}: {info['error'][:100]}\n"
            agent_input["error_guidance"] = error_guidance
        
        # Add outputs from dependent agents
        for input_ref in agent.inputs:
            if input_ref in outputs and input_ref not in ["user_data", "files_context", "error_memory"]:
                agent_input[f"input_from_{input_ref}"] = outputs[input_ref]
        
        return agent_input
    
    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get execution details"""
        db = await get_mongodb()
        execution = await db.get_collection("executions").find_one({"id": execution_id})
        
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        return execution