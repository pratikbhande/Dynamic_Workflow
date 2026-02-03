"""
Workflow Generator - AI-powered workflow creation with Prompt Library

This replaces your current workflow_generator.py
"""
from openai import AsyncOpenAI
import json
from typing import Dict, Any, List, Optional
from ...config import settings
from ...infrastructure.database.mongodb import get_mongodb
from ..prompts.prompt_library import get_prompt_library


class WorkflowGenerator:
    """
    Intelligent Workflow Generator
    
    Features:
    - Uses Prompt Library for consistent prompts
    - Detects tool requirements from natural language
    - Supports predefined tools
    - Parses user intent (vector DB choice, output format, etc.)
    - Generates credential-aware workflows
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-turbo"
        self.prompt_library = get_prompt_library()
    
    async def generate_workflow(
        self,
        task_description: str,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate workflow from natural language description
        
        Args:
            task_description: User's task in natural language
            user_id: User ID
            file_ids: Optional list of file IDs to use
            
        Returns:
            Complete workflow structure
        """
        
        print(f"\n{'='*80}")
        print(f"🧠 INTELLIGENT WORKFLOW GENERATION")
        print(f"{'='*80}\n")
        
        # Phase 1: Gather complete context
        print(f"📊 Phase 1: Gathering context...")
        context = await self._gather_complete_context(user_id, file_ids)
        print(f"   ✅ Context ready: {len(context['files'])} files, {len(context['system_capabilities'])} capability categories")
        
        # Phase 2: Parse user intent
        print(f"\n🔍 Phase 2: Analyzing user intent...")
        intent = await self._parse_user_intent(task_description, context)
        print(f"   ✅ Intent parsed:")
        print(f"      Goal: {intent['goal_type']}")
        print(f"      Output: {intent['desired_output']}")
        print(f"      Vector DB: {intent.get('vector_db_preference', 'chromadb')}")
        print(f"      Needs indexing: {intent.get('needs_indexing', False)}")
        
        # Phase 3: Design architecture
        print(f"\n🏗️  Phase 3: Designing workflow architecture...")
        workflow_structure = await self._design_architecture(
            task_description=task_description,
            intent=intent,
            context=context
        )
        print(f"   ✅ Architecture designed:")
        print(f"      Agents: {len(workflow_structure['agents'])}")
        print(f"      Edges: {len(workflow_structure['edges'])}")
        
        # Phase 4: Generate agent prompts using Prompt Library
        print(f"\n✍️  Phase 4: Generating agent prompts from library...")
        for i, agent in enumerate(workflow_structure['agents'], 1):
            print(f"   [{i}/{len(workflow_structure['agents'])}] {agent['name']}...")
            agent['detailed_prompt'] = await self._generate_agent_prompt(
                agent=agent,
                intent=intent,
                context=context,
                all_agents=workflow_structure['agents']
            )
            print(f"       ✅ Prompt generated ({len(agent['detailed_prompt'])} chars)")
        
        print(f"\n✅ Workflow ready: {workflow_structure['workflow_name']}")
        print(f"{'='*80}\n")
        
        return workflow_structure
    
    async def _gather_complete_context(
        self,
        user_id: str,
        file_ids: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Gather complete system and file context"""
        
        db = await get_mongodb()
        files_data = []
        
        # Get files with full data
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
            "system_capabilities": {
                "predefined_tools": {
                    "rag_builder": "Index documents into ChromaDB/FAISS/Pinecone",
                    "rag_chat": "Chat with indexed documents using RAG",
                    "report_generator": "Generate professional DOCX/PDF reports with charts",
                    "web_search": "Search web using Tavily API for current information"
                },
                "file_processors": {
                    "excel": "ExcelProcessor - read .xlsx/.xls files",
                    "csv": "CSVProcessor - process CSV data",
                    "pdf": "PDFProcessor - extract text from PDFs",
                    "txt": "TXTProcessor - read text files"
                },
                "vector_databases": {
                    "chromadb": "Local vector DB (default, easiest)",
                    "faiss": "Fast vector search, local",
                    "pinecone": "Cloud vector DB (requires API key)"
                },
                "code_execution": {
                    "python_executor": "Execute Python with auto-install of missing packages",
                    "working_dir": "/app/data/uploads",
                    "auto_install": True
                },
                "service_deployment": {
                    "streamlit": "Deploy interactive Streamlit apps",
                    "gradio": "Deploy Gradio interfaces",
                    "fastapi": "Deploy FastAPI endpoints"
                },
                "output_formats": {
                    "docx": "Word documents",
                    "pdf": "PDF reports",
                    "csv": "CSV exports",
                    "json": "JSON data"
                }
            }
        }
    
    def _format_file_context(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format file record for context"""
        
        context = {
            "file_id": file_record["id"],
            "filename": file_record["original_filename"],
            "type": file_record["file_type"],
            "path": file_record["file_path"],
            "text_content": file_record.get("text_content", "")[:1000]  # First 1000 chars
        }
        
        # Add structured data info
        processed = file_record.get("processed_data", {})
        if "sheets" in processed:
            context["sheets"] = {
                name: {
                    "columns": sheet.get("columns", []),
                    "rows": len(sheet.get("rows", []))
                }
                for name, sheet in processed["sheets"].items()
            }
        elif "data" in processed:
            context["data"] = {
                "columns": processed["data"].get("columns", []),
                "rows": len(processed["data"].get("rows", []))
            }
        
        return context
    
    async def _parse_user_intent(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse user intent from natural language
        
        Detects:
        - Goal type (chatbot, dashboard, report, analysis)
        - Desired output (API, UI, file, service)
        - Vector DB preference (chromadb, faiss, pinecone)
        - Output format preference (docx, pdf)
        - Whether indexing is needed
        """
        
        files_summary = "\n".join([
            f"- {f['filename']} ({f['type']})"
            for f in context['files']
        ]) if context['files'] else "No files"
        
        system_prompt = """Analyze user intent and extract key information.

CRITICAL: Parse natural language for specific preferences:
- Vector DB: If user mentions "FAISS", "Pinecone", or "ChromaDB", set vector_db_preference
- Output format: If user mentions "Word", "DOCX", "PDF", set output_format
- UI framework: If user mentions "Streamlit" or "Gradio", set ui_framework

Return JSON:
{
  "goal_type": "chatbot|dashboard|report|analysis|automation",
  "desired_output": "api|web_ui|file|service",
  "needs_visualization": true|false,
  "needs_indexing": true|false,
  "needs_api": true|false,
  "complexity": "simple|medium|complex",
  "vector_db_preference": "chromadb|faiss|pinecone",
  "output_format": "docx|pdf|csv|json",
  "ui_framework": "streamlit|gradio|none"
}"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Task: {task_description}\n\nAvailable Files:\n{files_summary}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        intent = json.loads(response.choices[0].message.content)
        
        # Set defaults if not specified
        intent.setdefault("vector_db_preference", "chromadb")
        intent.setdefault("output_format", "docx")
        intent.setdefault("ui_framework", "none")
        
        return intent
    
    async def _design_architecture(
        self,
        task_description: str,
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Design workflow architecture
        
        Strategy:
        - Use predefined tools when possible
        - Assign correct tool requirements
        - Build efficient agent graph
        """
        
        files_info = "\n".join([f"- {f['filename']}" for f in context['files']])
        
        predefined_tools_info = """
    PREDEFINED TOOLS (use these when possible):
    1. rag_builder - Index documents into vector DB
    Required for: document indexing, RAG setup
    Tools needed: ["rag_builder"]

    2. rag_chat - Chat with indexed documents
    Required for: chatbots, Q&A systems
    Tools needed: ["rag_chat"]

    3. report_generator - Generate DOCX/PDF reports with charts
    Required for: reports, documents, analysis output
    Tools needed: ["report_generator"]

    4. web_search - Search web for current information
    Required for: research, current data, solutions
    Tools needed: ["web_search"]

    5. python_executor - Execute Python code (ALWAYS include this)
    Required for: all agents as fallback
    Tools needed: ["python_executor"]
    """
        
        system_prompt = f"""You are a workflow architect. Design a multi-agent workflow using PREDEFINED TOOLS.

    {predefined_tools_info}

    CRITICAL TOOL ASSIGNMENT RULES:
    1. EVERY agent MUST have "python_executor" as first tool
    2. For document indexing → use "rag_builder" tool
    3. For chatbots → use "rag_chat" tool
    4. For reports → use "report_generator" tool
    5. For web research → use "web_search" tool
    6. Vector DB preference: {intent.get('vector_db_preference', 'chromadb')}
    7. Output format: {intent.get('output_format', 'docx')}

    YOU MUST RETURN VALID JSON WITH THIS EXACT STRUCTURE:
    {{
    "workflow_name": "Clear workflow name",
    "description": "What this workflow does",
    "agents": [
        {{
        "id": "agent_1",
        "name": "Agent Name",
        "type": "agent_type",
        "task": "Specific task",
        "required_tools": [
            {{"name": "python_executor", "type": "code_execution", "purpose": "Execute code"}},
            {{"name": "tool_name", "type": "predefined", "purpose": "Purpose"}}
        ],
        "inputs": ["user_data"],
        "outputs": ["output_name"]
        }}
    ],
    "edges": [
        {{"from_agent": "agent_1", "to_agent": "agent_2", "data_key": "output_name"}}
    ]
    }}

    MANDATORY FIELDS (must include all):
    - workflow_name (string)
    - description (string)
    - agents (array, at least 1 agent)
    - edges (array, can be empty)

    Each agent MUST have:
    - id (string)
    - name (string)
    - type (string)
    - task (string)
    - required_tools (array)
    - inputs (array)
    - outputs (array)

    RETURN ONLY VALID JSON. NO MARKDOWN. NO CODE BLOCKS."""
        
        user_prompt = f"""Task: {task_description}

    Intent Analysis:
    {json.dumps(intent, indent=2)}

    Available Files:
    {files_info}

    Design the complete workflow. Return ONLY the JSON structure."""
        
        print(f"\n{'─'*70}")
        print(f"🤖 Calling GPT-4 for architecture design...")
        print(f"{'─'*70}")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        raw_content = response.choices[0].message.content
        
        print(f"\n📥 Raw GPT-4 Response:")
        print(f"{'─'*70}")
        print(raw_content[:500])
        if len(raw_content) > 500:
            print(f"... (truncated, total length: {len(raw_content)} chars)")
        print(f"{'─'*70}\n")
        
        try:
            workflow = json.loads(raw_content)
            print(f"✅ JSON parsed successfully")
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON PARSING FAILED")
            print(f"{'─'*70}")
            print(f"Error: {str(e)}")
            print(f"Error position: line {e.lineno}, column {e.colno}")
            print(f"\nFull response content:")
            print(raw_content)
            print(f"{'─'*70}\n")
            raise ValueError(f"GPT-4 returned invalid JSON: {str(e)}")
        
        # VALIDATE required fields
        print(f"\n🔍 Validating workflow structure...")
        
        missing_fields = []
        if "workflow_name" not in workflow:
            missing_fields.append("workflow_name")
        if "description" not in workflow:
            missing_fields.append("description")
        if "agents" not in workflow:
            missing_fields.append("agents")
        if "edges" not in workflow:
            missing_fields.append("edges")
        
        if missing_fields:
            print(f"\n❌ VALIDATION FAILED - Missing required fields:")
            print(f"{'─'*70}")
            for field in missing_fields:
                print(f"  ❌ Missing: {field}")
            print(f"\nReceived workflow structure:")
            print(json.dumps(workflow, indent=2))
            print(f"{'─'*70}\n")
            raise ValueError(f"Workflow missing required fields: {missing_fields}")
        
        print(f"   ✅ workflow_name: {workflow['workflow_name']}")
        print(f"   ✅ description: {workflow['description'][:100]}...")
        print(f"   ✅ agents: {len(workflow['agents'])} agents")
        print(f"   ✅ edges: {len(workflow['edges'])} edges")
        
        # Validate agents
        print(f"\n🔍 Validating agents...")
        for i, agent in enumerate(workflow['agents'], 1):
            print(f"\n   Agent {i}: {agent.get('name', 'UNNAMED')}")
            
            required_agent_fields = ["id", "name", "type", "task", "required_tools", "inputs", "outputs"]
            missing_agent_fields = [f for f in required_agent_fields if f not in agent]
            
            if missing_agent_fields:
                print(f"      ❌ Missing fields: {missing_agent_fields}")
                print(f"      Agent data: {json.dumps(agent, indent=6)}")
                raise ValueError(f"Agent {i} missing required fields: {missing_agent_fields}")
            
            print(f"      ✅ ID: {agent['id']}")
            print(f"      ✅ Type: {agent['type']}")
            print(f"      ✅ Tools: {len(agent['required_tools'])}")
            print(f"      ✅ Inputs: {agent['inputs']}")
            print(f"      ✅ Outputs: {agent['outputs']}")
        
        # Validate edges
        if workflow['edges']:
            print(f"\n🔍 Validating edges...")
            for i, edge in enumerate(workflow['edges'], 1):
                print(f"\n   Edge {i}:")
                
                required_edge_fields = ["from_agent", "to_agent", "data_key"]
                missing_edge_fields = [f for f in required_edge_fields if f not in edge]
                
                if missing_edge_fields:
                    print(f"      ❌ Missing fields: {missing_edge_fields}")
                    raise ValueError(f"Edge {i} missing required fields: {missing_edge_fields}")
                
                print(f"      ✅ From: {edge['from_agent']} → To: {edge['to_agent']}")
                print(f"      ✅ Data key: {edge['data_key']}")
        
        print(f"\n✅ All validations passed")
        
        # Validate and fix tool assignments
        print(f"\n🔧 Fixing tool assignments...")
        workflow = self._validate_and_fix_tools(workflow, intent)
        print(f"   ✅ Tool assignments validated\n")
        
        return workflow
    
    def _validate_and_fix_tools(
        self,
        workflow: Dict[str, Any],
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and fix tool assignments"""
        
        for agent in workflow.get("agents", []):
            # Ensure required_tools exists
            if "required_tools" not in agent:
                agent["required_tools"] = []
            
            # FORCE python_executor as first tool
            has_executor = any(
                tool.get("name") == "python_executor"
                for tool in agent["required_tools"]
            )
            
            if not has_executor:
                agent["required_tools"].insert(0, {
                    "name": "python_executor",
                    "type": "code_execution",
                    "purpose": "Execute Python code"
                })
            
            # Add vector_db_preference to RAG tools
            for tool in agent["required_tools"]:
                if tool.get("name") in ["rag_builder", "rag_chat"]:
                    if "config" not in tool:
                        tool["config"] = {}
                    tool["config"]["vector_db"] = intent.get("vector_db_preference", "chromadb")
        
        return workflow
    
    async def _generate_agent_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any],
        all_agents: List[Dict[str, Any]]
    ) -> str:
        """
        Generate agent prompt using Prompt Library
        """
        
        agent_type = agent.get("type", "generic")
        agent_name = agent.get("name", "Agent")
        task = agent.get("task", "Execute task")
        
        # Check if we have a specific prompt for this agent type
        if agent_type in ["rag_builder", "document_indexer"]:
            return await self._generate_rag_builder_prompt(agent, intent, context)
        
        elif agent_type in ["rag_chat", "chat_backend", "chatbot"]:
            return await self._generate_rag_chat_prompt(agent, intent, context)
        
        elif agent_type in ["report_generator", "report_builder"]:
            return await self._generate_report_prompt(agent, intent, context)
        
        elif agent_type in ["web_researcher", "web_search"]:
            return await self._generate_web_search_prompt(agent, intent, context)
        
        elif agent_type in ["ui_builder", "streamlit", "streamlit_builder", "dashboard"]:  # NEW
            return await self._generate_streamlit_prompt(agent, intent, context)
        
        else:
            # Generic agent prompt
            return await self._generate_generic_prompt(agent, intent, context)


    async def _generate_streamlit_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate Streamlit builder prompt from library"""
        
        # Detect what data source to use
        data_source = "RAG chat function"
        if context["files"]:
            data_source = f"Files: {[f['filename'] for f in context['files']]}"
        
        # Build features list
        features = [
            "Sidebar with API key input",
            "Chat interface",
            "Source attribution",
            "Custom styling"
        ]
        
        # Check if prompt exists in library
        if "streamlit_builder" in self.prompt_library.prompts:
            prompt = self.prompt_library.get_prompt(
                "streamlit_builder",
                variables={
                    "task": agent.get("task", "Build Streamlit app"),
                    "data_source": data_source,
                    "features": ", ".join(features)
                }
            )
        else:
            # Fallback to generic
            prompt = await self._generate_generic_prompt(agent, intent, context)
        
        return prompt
    
    async def _generate_rag_builder_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate RAG builder prompt from library"""
        
        # Get file paths
        file_paths = [f["path"] for f in context["files"]]
        
        # Get vector DB preference
        vector_db = intent.get("vector_db_preference", "chromadb")
        
        # Get prompt from library
        prompt = self.prompt_library.get_prompt(
            "rag_builder",
            variables={
                "task": agent.get("task", "Index documents"),
                "vector_db_type": vector_db,
                "collection_name": "rag_documents",
                "file_paths": json.dumps(file_paths),
                "chunk_size": "800",
                "chunk_overlap": "200"
            }
        )
        
        return prompt
    
    async def _generate_rag_chat_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate RAG chat prompt from library"""
        
        vector_db = intent.get("vector_db_preference", "chromadb")
        
        prompt = self.prompt_library.get_prompt(
            "rag_chat",
            variables={
                "query": "{user_query}",  # Placeholder for runtime
                "vector_db_type": vector_db,
                "collection_name": "rag_documents",
                "top_k": "3"
            }
        )
        
        return prompt
    
    async def _generate_report_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate report generator prompt from library"""
        
        output_format = intent.get("output_format", "docx")
        
        prompt = self.prompt_library.get_prompt(
            "report_generator",
            variables={
                "task": agent.get("task", "Generate report"),
                "data": "{analysis_data}",  # Placeholder
                "output_format": output_format,
                "chart_title": "Analysis Results",
                "report_title": "Analysis Report",
                "executive_summary": "Summary of findings",
                "analysis_content": "Detailed analysis",
                "conclusion": "Conclusions and recommendations",
                "timestamp": "{timestamp}"
            }
        )
        
        return prompt
    
    async def _generate_web_search_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate web search prompt from library"""
        
        prompt = self.prompt_library.get_prompt(
            "web_search",
            variables={
                "query": agent.get("task", "Search query"),
                "max_results": "5"
            }
        )
        
        return prompt
    
    async def _generate_generic_prompt(
        self,
        agent: Dict[str, Any],
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate generic agent prompt"""
        
        # Build comprehensive generic prompt
        files_context = self._build_files_context(context["files"])
        system_knowledge = self._build_system_knowledge(context)
        
        prompt = f"""YOU ARE: {agent['name']}
TYPE: {agent['type']}

MISSION: {agent['task']}

CRITICAL RULES:
1. EXECUTE the task - don't just describe it
2. Write ACTUAL CODE that runs
3. Use full file paths: /app/data/uploads/filename
4. Return ACTUAL RESULTS
5. Handle errors gracefully

{'='*70}
SYSTEM KNOWLEDGE
{'='*70}

{system_knowledge}

{'='*70}
AVAILABLE FILES
{'='*70}

{files_context}

{'='*70}
YOUR APPROACH
{'='*70}

1. UNDERSTAND the task completely
2. WRITE Python code to accomplish it
3. EXECUTE the code
4. RETURN the actual result

IMPORTANT:
- Use predefined tools when available (check required_tools)
- Auto-install handles missing packages
- Save outputs to /app/data/uploads for download
- Return file paths, URLs, or structured data

EXECUTE NOW:
"""
        
        return prompt
    
    def _build_system_knowledge(self, context: Dict[str, Any]) -> str:
        """Build system knowledge string"""
        
        caps = context["system_capabilities"]
        knowledge = []
        
        knowledge.append("PREDEFINED TOOLS:")
        for name, desc in caps["predefined_tools"].items():
            knowledge.append(f"  • {name}: {desc}")
        
        knowledge.append("\nVECTOR DATABASES:")
        for name, desc in caps["vector_databases"].items():
            knowledge.append(f"  • {name}: {desc}")
        
        knowledge.append("\nCODE EXECUTION:")
        knowledge.append(f"  • Python with auto-install")
        knowledge.append(f"  • Working directory: {caps['code_execution']['working_dir']}")
        
        knowledge.append("\nOUTPUT FORMATS:")
        for fmt, desc in caps["output_formats"].items():
            knowledge.append(f"  • {fmt}: {desc}")
        
        return "\n".join(knowledge)
    
    def _build_files_context(self, files: List[Dict[str, Any]]) -> str:
        """Build files context string"""
        
        if not files:
            return "No files uploaded"
        
        lines = []
        for f in files:
            lines.append(f"\n📄 File: {f['filename']}")
            lines.append(f"   Path: {f['path']}")
            lines.append(f"   Type: {f['type']}")
            
            if "sheets" in f:
                lines.append(f"   Sheets: {list(f['sheets'].keys())}")
                for sheet_name, sheet_info in f["sheets"].items():
                    lines.append(f"     • {sheet_name}: {sheet_info['columns'][:5]}... ({sheet_info['rows']} rows)")
            
            elif "data" in f:
                lines.append(f"   Columns: {f['data']['columns'][:5]}...")
                lines.append(f"   Rows: {f['data']['rows']}")
            
            if f.get("text_content"):
                preview = f["text_content"][:200].replace("\n", " ")
                lines.append(f"   Preview: {preview}...")
        
        return "\n".join(lines)