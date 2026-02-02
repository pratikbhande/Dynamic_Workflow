"""Workflow Generator - AI-powered workflow creation with intelligent architecture"""
from openai import AsyncOpenAI
import json
from typing import Dict, Any, List
from ...config import settings
from ...infrastructure.database.mongodb import get_mongodb
from .workflow_analyzer import WorkflowAnalyzer


class WorkflowGenerator:
    """Generates multi-agent workflows with intelligent architecture detection"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.analyzer = WorkflowAnalyzer()
    
    async def generate_workflow(
        self,
        task_description: str,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Generate workflow with intelligent architecture"""
        
        context = await self._gather_complete_context(user_id, file_ids)
        
        print(f"\n{'='*80}")
        print(f"📋 WORKFLOW GENERATION")
        print(f"{'='*80}")
        print(f"Files: {len(context['files'])}")
        print(f"Task: {task_description}")
        
        # STEP 1: Generate workflow structure
        print(f"\n📐 Step 1: Generating workflow structure...")
        workflow_structure = await self._generate_workflow_structure(
            task_description=task_description,
            context=context
        )
        
        print(f"✅ Structure created: {len(workflow_structure['agents'])} agents")
        
        # STEP 1.5: Ensure proper architecture
        workflow_structure = self._ensure_proper_architecture(
            workflow_structure,
            task_description
        )
        
        # STEP 2: Generate detailed prompts
        print(f"\n📝 Step 2: Generating detailed prompts for each agent...")
        for i, agent in enumerate(workflow_structure['agents'], 1):
            print(f"  [{i}/{len(workflow_structure['agents'])}] {agent['name']}...", end=" ")
            
            detailed_prompt = await self._generate_agent_detailed_prompt(
                agent=agent,
                context=context,
                task_description=task_description,
                all_agents=workflow_structure['agents']
            )
            
            agent['detailed_prompt'] = detailed_prompt
            print(f"✅ ({len(detailed_prompt)} chars)")
        
        print(f"\n✅ Workflow '{workflow_structure['workflow_name']}' ready!")
        print(f"{'='*80}\n")
        
        return workflow_structure
    
    async def _gather_complete_context(
        self,
        user_id: str,
        file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Gather ALL context"""
        
        db = await get_mongodb()
        
        files_data = []
        if file_ids:
            for file_id in file_ids:
                file_record = await db.get_collection("files").find_one({"id": file_id})
                if file_record:
                    files_data.append(self._format_file_for_context(file_record))
        else:
            cursor = db.get_collection("files").find({"user_id": user_id})
            all_files = await cursor.to_list(length=50)
            for file_record in all_files:
                files_data.append(self._format_file_for_context(file_record))
        
        context = {
            "files": files_data,
            "available_tools": {
                "vector_databases": {
                    "chromadb": {
                        "description": "Embedded vector database",
                        "use_for": "RAG, semantic search",
                        "capabilities": ["index_documents", "search_similar"]
                    }
                },
                "mcps": {
                    "filesystem": {"description": "File operations", "available": True},
                    "mongodb": {"description": "Database operations", "available": True},
                    "slack": {"description": "Notifications", "available": bool(settings.SLACK_BOT_TOKEN)},
                    "websearch": {"description": "Web search", "available": bool(getattr(settings, 'TAVILY_API_KEY', None))}
                },
                "code_execution": {
                    "python_executor": {"description": "Execute Python", "auto_install": True}
                }
            }
        }
        
        return context
    
    def _format_file_for_context(self, file_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format file for context"""
        return {
            "file_id": file_record["id"],
            "filename": file_record["original_filename"],
            "type": file_record["file_type"],
            "path": file_record["file_path"],
            "text_content": file_record.get("text_content", "")[:5000]  # More context
        }
    
    async def _generate_workflow_structure(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level structure"""
        
        system_prompt = self._get_structure_generation_prompt(context)
        user_prompt = self._get_user_prompt_for_structure(task_description, context)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _get_structure_generation_prompt(self, context: Dict[str, Any]) -> str:
        """System prompt for structure"""
        
        files_info = []
        for file in context["files"]:
            files_info.append(f"- {file['filename']} ({file['type']})")
        
        return f"""You are a workflow architect. Generate a multi-agent workflow structure.

    FILES AVAILABLE: {', '.join(files_info) if files_info else 'None'}

    AGENT TYPES AND THEIR REQUIRED TOOLS:

    1. rag_builder - Indexes documents into vector database
    MUST HAVE: {{"name": "chromadb", "type": "vector_db", "purpose": "index documents"}}
    MUST HAVE: {{"name": "python_executor", "type": "code_execution", "purpose": "process files"}}

    2. chat_endpoint_builder - Creates /chat API endpoint
    MUST HAVE: {{"name": "python_executor", "type": "code_execution", "purpose": "create endpoint"}}
    Note: This agent will use run_chat_endpoint tool (auto-added by system)

    3. streamlit_ui_builder - Deploy Streamlit interface
    MUST HAVE: {{"name": "python_executor", "type": "code_execution", "purpose": "deploy ui"}}

    CRITICAL RULES:
    - EVERY agent MUST have "required_tools" array with at least one tool
    - rag_builder MUST have chromadb in required_tools
    - Agent IDs: agent_1, agent_2, etc.
    - Inputs: ["user_data"] for first agent, ["agent_X"] for dependent agents

    OUTPUT FORMAT (JSON):
    {{
    "workflow_name": "Descriptive Name",
    "description": "What this workflow does",
    "agents": [
        {{
        "id": "agent_1",
        "name": "Document Indexer",
        "type": "rag_builder",
        "task": "Index uploaded documents into vector database",
        "required_tools": [
            {{"name": "chromadb", "type": "vector_db", "purpose": "index documents"}},
            {{"name": "python_executor", "type": "code_execution", "purpose": "process files"}}
        ],
        "inputs": ["user_data"],
        "outputs": ["collection_name"]
        }},
        {{
        "id": "agent_2",
        "name": "Chat Endpoint",
        "type": "chat_endpoint_builder",
        "task": "Create /chat API endpoint with RAG",
        "required_tools": [
            {{"name": "python_executor", "type": "code_execution", "purpose": "create endpoint"}}
        ],
        "inputs": ["agent_1"],
        "outputs": ["chat_url"]
        }}
    ],
    "edges": [
        {{"from_agent": "agent_1", "to_agent": "agent_2", "data_key": "collection_name"}}
    ]
    }}

    REMEMBER: required_tools array is MANDATORY for every agent!"""
    
    def _get_user_prompt_for_structure(self, task_description: str, context: Dict[str, Any]) -> str:
        """User prompt"""
        return f"TASK: {task_description}\nCreate structure only."
    
    def _ensure_proper_architecture(self, workflow_dict: Dict[str, Any], task_description: str) -> Dict[str, Any]:
        """Ensure proper architecture"""
        
        analysis = self.analyzer.analyze_task(task_description)
        
        print(f"\n🏗️  Architecture: {analysis['architecture']}")
        
        has_chat = any(a['type'] == 'chat_endpoint_builder' for a in workflow_dict['agents'])
        
        if analysis['needs_chat_endpoint'] and not has_chat:
            print("📡 Adding chat endpoint...")
            
            backend_id = workflow_dict['agents'][-1]['id']
            
            chat_agent = {
                "id": f"agent_{len(workflow_dict['agents']) + 1}",
                "name": "Chat Endpoint",
                "type": "chat_endpoint_builder",
                "task": "Create /chat API endpoint",
                "required_tools": [{"name": "python_executor", "type": "code_execution"}],
                "inputs": [backend_id],
                "outputs": ["chat_url"]
            }
            
            workflow_dict['agents'].append(chat_agent)
            workflow_dict['edges'].append({
                "from_agent": backend_id,
                "to_agent": chat_agent['id'],
                "data_key": "output"
            })
        
        return workflow_dict
    
    async def _generate_agent_detailed_prompt(
        self,
        agent: Dict[str, Any],
        context: Dict[str, Any],
        task_description: str,
        all_agents: List[Dict[str, Any]]
    ) -> str:
        """Generate TOOL-CENTRIC prompts"""
        
        if agent['type'] == 'rag_builder':
            return self._create_rag_builder_prompt(context)
        elif agent['type'] == 'chat_endpoint_builder':
            return self._create_chat_endpoint_prompt(context)
        else:
            return self._create_generic_prompt(agent, context)
    
    def _create_rag_builder_prompt(self, context: Dict[str, Any]) -> str:
        """RAG builder - Uses actual tools correctly"""
        
        # Get file info
        files_info = []
        for file in context['files']:
            files_info.append(f"- {file['filename']} at {file['path']}")
        
        files_list = '\n'.join(files_info) if files_info else 'No files uploaded'
        
        # Build file paths for code
        file_paths_code = '\n'.join(f'    "{file["path"]}",' for file in context['files'])
        
        return f"""You are a RAG system builder. Your ONLY job: Index documents into vector database.

    AVAILABLE FILES:
    {files_list}

    YOUR TOOLS:
    1. execute_python - Run Python code to read and chunk files
    2. add_to_vector_db - Add documents to vector database (requires JSON input)

    YOUR TASK IN 2 STEPS:

    STEP 1: Read and chunk the files using execute_python
    -------------------------------------------------------
    Call execute_python with this code (file paths are already set):

    import json
    import os

    all_chunks = []

    file_paths = [
    {file_paths_code}
    ]

    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {{{{file_path}}}}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunk_size = 800
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size].strip()
                if chunk:
                    all_chunks.append(chunk)
            
            print(f"Processed {{{{file_path}}}}: {{{{len(all_chunks)}}}} total chunks")
        except Exception as e:
            print(f"Error processing {{{{file_path}}}}: {{{{e}}}}")

    result = {{"documents": all_chunks, "total": len(all_chunks)}}
    print("CHUNKS_READY:", json.dumps(result))


    STEP 2: Index chunks using add_to_vector_db
    --------------------------------------------
    After step 1 completes, look for "CHUNKS_READY:" in the output.
    Extract the documents array and call add_to_vector_db.

    Example: If output shows CHUNKS_READY: {{"documents": ["chunk1", "chunk2"], "total": 2}}
    Then call: add_to_vector_db with input {{"documents": ["chunk1", "chunk2"]}}

    CRITICAL RULES:
    - Do NOT import chromadb or vector_databases
    - Do NOT write your own indexing code
    - Use the TWO TOOLS: execute_python then add_to_vector_db
    - Output format: "SUCCESS: Indexed X documents into collection 'rag_documents'"

    REMEMBER: Double curly braces {{{{ }}}} in code are just regular braces."""
    
    def _create_chat_endpoint_prompt(self, context: Dict[str, Any]) -> str:
        """Chat endpoint builder - Deploy working FastAPI service"""
        
        return f"""You are a chat endpoint builder. Your job: Create a WORKING /chat API endpoint.

    CONTEXT:
    - Documents are indexed in ChromaDB collection: "rag_documents"
    - Collection location: /app/data/chromadb
    - OpenAI API key is available in environment

    YOUR TOOLS:
    - run_chat_endpoint: Takes FastAPI code and RUNS it as a background service

    YOUR TASK:

    Generate this FastAPI code and pass it to run_chat_endpoint tool.
    IMPORTANT: In the code below, {{{{variable}}}} means regular Python variable, not template.

    CODE TO GENERATE:

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from openai import OpenAI
    import os

    app = FastAPI()

    try:
        chroma_client = chromadb.Client(
            ChromaSettings(
                persist_directory="/app/data/chromadb",
                anonymized_telemetry=False
            )
        )
        collection = chroma_client.get_or_create_collection("rag_documents")
        print("Collection ready")
    except Exception as e:
        print(f"ChromaDB error: {{{{e}}}}")
        collection = None

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    class ChatRequest(BaseModel):
        message: str

    @app.post("/chat")
    async def chat(request: ChatRequest):
        try:
            context_text = ""
            if collection:
                try:
                    results = collection.query(
                        query_texts=[request.message],
                        n_results=3
                    )
                    if results and results.get('documents') and len(results['documents']) > 0:
                        context_text = "\\n".join(results['documents'][0])
                except Exception as e:
                    print(f"Query error: {{{{e}}}}")
            
            if not context_text:
                context_text = "No specific context available."
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {{"role": "system", "content": f"Answer based on: {{{{context_text}}}}"}},
                    {{"role": "user", "content": request.message}}
                ]
            )
            
            return {{
                "response": response.choices[0].message.content,
                "context_used": bool(context_text)
            }}
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health():
        return {{"status": "healthy", "collection": collection is not None}}


    EXECUTION STEPS:
    1. Copy the code above EXACTLY (the {{{{}}}} in code are regular braces)
    2. Call: run_chat_endpoint with the complete code as input
    3. Tool returns URL like: http://localhost:8105/chat
    4. Return that URL to user

    Your final output must be: "Chat endpoint deployed at [URL]"
    """
    
    def _create_generic_prompt(self, agent: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generic prompt"""
        return f"TASK: {agent['task']}\nUse available tools to accomplish this."
    
    async def modify_workflow(self, workflow_id: str, modifications: str, user_id: str) -> Dict[str, Any]:
        """Modify workflow"""
        db = await get_mongodb()
        workflow_doc = await db.get_collection("workflows").find_one({"id": workflow_id})
        
        if not workflow_doc:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        original_task = workflow_doc.get('description', '')
        modified_task = f"{original_task}\n\nMODIFICATIONS: {modifications}"
        file_ids = workflow_doc.get('file_ids')
        
        return await self.generate_workflow(
            task_description=modified_task,
            user_id=user_id,
            file_ids=file_ids
        )