from openai import AsyncOpenAI
import json
from typing import Dict, Any, List
from ...config import settings
from ...infrastructure.database.mongodb import get_mongodb

class WorkflowGenerator:
    """Generates multi-agent workflows with FULL CONTEXT"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    async def generate_workflow(
        self,
        task_description: str,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Generate workflow with complete file and tool context"""
        
        # Get complete context
        context = await self._gather_complete_context(user_id, file_ids)
        
        # Generate workflow with full context
        system_prompt = self._get_enhanced_system_prompt(context)
        user_prompt = self._get_enhanced_user_prompt(task_description, context)
        
        print(f"\n{'='*80}")
        print(f"📋 WORKFLOW GENERATION WITH FULL CONTEXT")
        print(f"{'='*80}")
        print(f"Files: {len(context['files'])}")
        print(f"Available Tools: {len(context['available_tools'])}")
        print(f"\nGenerating workflow...\n")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        workflow_json = json.loads(response.choices[0].message.content)
        
        # Enhance agent prompts with file context
        workflow = await self._enhance_agent_prompts_with_context(
            workflow_json,
            context
        )
        
        return workflow
    
    async def _gather_complete_context(
        self,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Gather ALL context: files, tools, MCPs, vector DBs"""
        
        db = await get_mongodb()
        
        # Get files
        files_data = []
        if file_ids:
            for file_id in file_ids:
                file_record = await db.get_collection("files").find_one({"id": file_id})
                if file_record:
                    files_data.append(self._format_file_for_context(file_record))
        else:
            # Get all user files
            cursor = db.get_collection("files").find({"user_id": user_id})
            all_files = await cursor.to_list(length=50)
            
            for file_record in all_files:
                files_data.append(self._format_file_for_context(file_record))
        
        # Available tools and capabilities
        context = {
            "files": files_data,
            "available_tools": {
                "vector_databases": {
                    "chromadb": {
                        "description": "Embedded vector database, no setup needed",
                        "use_for": "RAG, semantic search on documents",
                        "capabilities": ["index_documents", "search_similar"]
                    },
                    "faiss": {
                        "description": "High-performance in-memory vector search",
                        "use_for": "Fast similarity search",
                        "capabilities": ["index_embeddings", "nearest_neighbor_search"]
                    }
                },
                "mcps": {
                    "filesystem": {
                        "description": "Read/write files",
                        "capabilities": ["read_file", "write_file", "list_files"],
                        "available": True
                    },
                    "mongodb": {
                        "description": "Database operations",
                        "capabilities": ["insert", "find", "update", "delete"],
                        "available": True
                    },
                    "slack": {
                        "description": "Send notifications",
                        "capabilities": ["send_message"],
                        "available": bool(settings.SLACK_BOT_TOKEN)
                    }
                },
                "code_execution": {
                    "python_executor": {
                        "description": "Execute Python code with pandas, numpy, matplotlib",
                        "capabilities": ["execute_python_code"],
                        "libraries_available": [
                            "pandas", "numpy", "matplotlib", "json",
                            "re", "datetime", "collections"
                        ],
                        "file_access": True
                    }
                }
            },
            "execution_context": {
                "upload_directory": settings.UPLOAD_DIR,
                "can_access_files": True,
                "can_save_outputs": True
            }
        }
        
        return context
    
    def _format_file_for_context(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format a file record for workflow generation context"""
        
        formatted = {
            "file_id": file_record["id"],
            "filename": file_record["original_filename"],
            "type": file_record["file_type"],
            "path": file_record["file_path"],
            "processed_data": file_record["processed_data"],
            "text_content": file_record["text_content"][:2000],
            "full_text_available": True
        }
        
        return formatted
    
    def _get_enhanced_system_prompt(self, context: Dict[str, Any]) -> str:
        """Generate system prompt with complete context"""
        
        # Format files information
        files_info = []
        for file in context["files"]:
            file_str = f"\nFile: {file['filename']} (ID: {file['file_id']})"
            file_str += f"\n  Type: {file['type']}"
            file_str += f"\n  Path: {file['path']}"
            
            processed_data = file.get('processed_data', {})
            
            # Handle Excel files
            if file['type'] in ['.xlsx', '.xls'] and 'sheets' in processed_data:
                for sheet_name, sheet_data in processed_data['sheets'].items():
                    file_str += f"\n  Sheet '{sheet_name}':"
                    file_str += f"\n    Columns: {', '.join(sheet_data.get('columns', []))}"
                    file_str += f"\n    Rows: {sheet_data.get('summary', {}).get('total_rows', 0)}"
                    
                    # Show sample data
                    sample_rows = sheet_data.get('rows', [])[:3]
                    if sample_rows:
                        file_str += f"\n    Sample Data: {json.dumps(sample_rows[:2], indent=6)}"
            
            # Handle CSV files
            elif file['type'] == '.csv' and 'data' in processed_data:
                data = processed_data['data']
                file_str += f"\n  Columns: {', '.join(data.get('columns', []))}"
                file_str += f"\n  Rows: {data.get('summary', {}).get('total_rows', 0)}"
                
                # Show sample data
                sample_rows = data.get('rows', [])[:3]
                if sample_rows:
                    file_str += f"\n  Sample Data: {json.dumps(sample_rows[:2], indent=4)}"
            
            # Handle PDF files
            elif file['type'] == '.pdf' and 'data' in processed_data:
                pdf_data = processed_data.get('data', {})
                file_str += f"\n  Pages: {pdf_data.get('total_pages', 0)}"
                
                # Show text preview
                text_preview = file.get('text_content', '')[:300]
                if text_preview:
                    file_str += f"\n  Content Preview: {text_preview}..."
            
            files_info.append(file_str)
        
        files_section = "\n".join(files_info) if files_info else "No files uploaded"
        
        # Format tools information
        tools_section = f"""
VECTOR DATABASES:
{json.dumps(context['available_tools']['vector_databases'], indent=2)}

MCP TOOLS:
{json.dumps(context['available_tools']['mcps'], indent=2)}

CODE EXECUTION:
{json.dumps(context['available_tools']['code_execution'], indent=2)}
"""
        
        return f"""You are an expert workflow architect. You create multi-agent workflows with COMPLETE, EXECUTABLE details.

CRITICAL RULES:
1. Agent prompts MUST include EXACT file paths and column names
2. Agent prompts MUST include STEP-BY-STEP executable instructions
3. For code execution, provide COMPLETE working Python code
4. Use ACTUAL data from files - don't make up column names
5. Specify exact tool usage with parameters
6. Define clear, parseable output formats

AVAILABLE CONTEXT:

FILES UPLOADED:
{files_section}

{tools_section}

EXECUTION ENVIRONMENT:
- Upload directory: {context['execution_context']['upload_directory']}
- File access: Enabled
- Can save outputs: Yes

AGENT TYPES & TEMPLATES:

1. data_processor
   - Use when: Need to load and process Excel/CSV files
   - Tools: python_executor, filesystem
   - Prompt must include: Exact file path, column names, pandas code

2. rag_builder
   - Use when: Need to index documents for semantic search
   - Tools: chromadb or faiss, filesystem
   - Prompt must include: File path, chunking strategy, metadata

3. analyzer
   - Use when: Need to analyze data from previous agent
   - Tools: Based on requirements
   - Prompt must include: Input structure, analysis steps
   
4. report_generator
   - Use when: Generate final output/report
   - Tools: filesystem, slack (optional)
   - Prompt must include: Input structure, output format

# Find this section and replace:
OUTPUT JSON FORMAT:
{{
  "workflow_name": "Descriptive name",
  "description": "What this workflow does",
  "agents": [
    {{
      "id": "agent_1",
      "type": "data_processor|rag_builder|analyzer|report_generator",
      "name": "Clear agent name",
      "task": "High-level task description",
      "detailed_prompt": "COMPLETE prompt with file paths, column names, code, steps",
      "required_tools": [
        {{
          "name": "python_executor|chromadb|faiss|filesystem|mongodb|slack",
          "type": "code_execution|vector_db|mcp",
          "purpose": "Why needed",
          "config": {{}}
        }}
      ],
      "inputs": ["agent_id" or "user_data"],
      "outputs": ["output_key"],
      "output_format": "JSON|Text|Markdown - be specific"
    }}
  ],
  "edges": [
    {{"from_agent": "agent_1", "to_agent": "agent_2", "data_key": "output_key"}}
  ]
}}

REMEMBER:
- Use ACTUAL file paths from the files list
- Use ACTUAL column names from sample data
- Provide EXECUTABLE code, not pseudocode
- Be SPECIFIC about data structures"""
    
    def _get_enhanced_user_prompt(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> str:
        """Create user prompt with task and context reference"""
        
        files_summary = []
        for file in context["files"]:
            files_summary.append(f"- {file['filename']} ({file['type']})")
        
        return f"""USER TASK: {task_description}

FILES AVAILABLE:
{chr(10).join(files_summary)}

Create a complete workflow that accomplishes this task using the available files and tools.

IMPORTANT:
- Include ALL file details (paths, columns) in agent prompts
- Write EXECUTABLE Python code where needed
- Specify exact tool parameters
- Define clear data flow between agents"""
    
    async def _enhance_agent_prompts_with_context(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Further enhance agent prompts if needed"""
        
        # Already enhanced in main generation
        # This is a placeholder for additional processing if needed
        
        print(f"\n✅ Generated {len(workflow['agents'])} agents:")
        for agent in workflow["agents"]:
            print(f"   - {agent['name']} ({agent['type']})")
            print(f"     Tools: {[t['name'] for t in agent.get('required_tools', [])]}")
        
        return workflow