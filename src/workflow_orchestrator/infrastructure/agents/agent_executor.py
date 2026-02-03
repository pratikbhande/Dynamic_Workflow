"""
Agent Executor - Intelligent execution with 5-retry strategy

This replaces your current agent_executor.py
"""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from ..tools.tool_registry import ToolRegistry
from ...domain.services.error_memory import ErrorMemory
from ...domain.credentials.credential_manager import get_credential_manager
from ...config import settings
import json
import time


class DynamicAgentExecutor:
    """
    Agent Executor with intelligent 5-retry strategy
    
    Retry Strategy:
    1. Normal execution
    2. Fix obvious errors (imports, syntax)
    3. Web search for solution
    4. Rewrite code from scratch
    5. Try alternative approach
    """
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.error_memory = ErrorMemory()
        self.credential_manager = get_credential_manager()
        self.max_retries = 5
    
    async def execute_agent_with_retry(
        self,
        agent_config: Dict[str, Any],
        input_data: Any,
        max_retries: int = None
    ) -> Dict[str, Any]:
        """
        Execute agent with 5-level intelligent retry
        
        Args:
            agent_config: Agent configuration
            input_data: Input data for agent
            max_retries: Override default max retries
            
        Returns:
            Execution result
        """
        
        max_retries = max_retries or self.max_retries
        
        print(f"\n{'='*70}")
        print(f"🤖 Executing Agent: {agent_config['name']}")
        print(f"   Type: {agent_config['type']}")
        print(f"{'='*70}")
        
        last_error = None
        error_history = []
        
        for attempt in range(1, max_retries + 1):
            print(f"\n{'─'*70}")
            print(f"🔄 Attempt {attempt}/{max_retries}")
            print(f"{'─'*70}")
            
            try:
                # Determine strategy based on attempt
                if attempt == 1:
                    strategy = "normal"
                    print("   Strategy: Normal execution")
                elif attempt == 2:
                    strategy = "fix_obvious"
                    print("   Strategy: Fix obvious errors")
                elif attempt == 3:
                    strategy = "web_search"
                    print("   Strategy: Web search for solution")
                elif attempt == 4:
                    strategy = "rewrite"
                    print("   Strategy: Rewrite from scratch")
                else:
                    strategy = "alternative"
                    print("   Strategy: Try alternative approach")
                
                # Enhance prompt based on strategy
                enhanced_config = await self._enhance_prompt_with_strategy(
                    agent_config=agent_config,
                    strategy=strategy,
                    error_history=error_history
                )
                
                # Execute
                result = await self.execute_agent(enhanced_config, input_data)
                
                # Check if successful
                if self._is_execution_successful(result):
                    print(f"\n✅ Agent succeeded on attempt {attempt}")
                    
                    # Store success in error memory if this was a retry
                    if attempt > 1 and error_history:
                        await self.error_memory.store_solution(
                            error_message=error_history[-1]["error"],
                            solution=f"Strategy '{strategy}' worked",
                            success=True
                        )
                    
                    return {
                        "agent_id": agent_config["id"],
                        "output": result["output"],
                        "status": "completed",
                        "attempts": attempt
                    }
                else:
                    # Consider it a failure
                    error_msg = "Agent returned description instead of execution"
                    raise Exception(error_msg)
                
            except Exception as e:
                last_error = str(e)
                error_history.append({
                    "attempt": attempt,
                    "strategy": strategy,
                    "error": last_error,
                    "timestamp": time.time()
                })
                
                print(f"   ❌ Attempt {attempt} failed: {last_error[:200]}")
                
                if attempt < max_retries:
                    print(f"   ⏳ Retrying with next strategy...")
                    time.sleep(1)  # Brief pause between retries
        
        # All retries exhausted
        print(f"\n❌ Agent failed after {max_retries} attempts")
        
        # Store failure in error memory
        await self.error_memory.store_solution(
            error_message=last_error,
            solution="No solution found after all retries",
            success=False
        )
        
        return {
            "agent_id": agent_config["id"],
            "output": f"Failed after {max_retries} attempts. Last error: {last_error}",
            "status": "failed",
            "error_history": error_history
        }
    
    async def execute_agent(
        self,
        agent_config: Dict[str, Any],
        input_data: Any
    ) -> Dict[str, Any]:
        """Execute a single agent attempt"""
        
        try:
            # 1. Provision tools
            provisioned_tools = await self._provision_tools(
                agent_id=agent_config["id"],
                required_tools=agent_config.get("required_tools", [])
            )
            
            # 2. Get credentials for tools
            credentials = await self._get_tool_credentials(
                user_id=agent_config.get("user_id", "default_user"),
                provisioned_tools=provisioned_tools
            )
            
            # 3. Create LangChain tools
            langchain_tools = await self._create_langchain_tools(
                provisioned_tools,
                credentials
            )
            
            print(f"   Tools available: {len(langchain_tools)}")
            for tool in langchain_tools:
                print(f"     - {tool.name}")
            
            # 4. Prepare input
            agent_input = self._prepare_comprehensive_input(agent_config, input_data)
            
            # 5. Create LLM
            llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4-turbo",
                temperature=0.3
            )
            
            # 6. Execute
            if langchain_tools:
                output = await self._execute_with_tools(
                    llm, langchain_tools, agent_config, agent_input
                )
            else:
                output = await self._execute_without_tools(
                    llm, agent_config, agent_input
                )
            
            # 7. Parse output
            parsed_output = self._parse_output(output)
            
            print(f"\n   ✅ Execution completed")
            
            # 8. Cleanup
            await self.tool_registry.cleanup_tools(provisioned_tools)
            
            return {
                "agent_id": agent_config["id"],
                "output": parsed_output,
                "status": "completed"
            }
            
        except Exception as e:
            print(f"\n   ❌ Execution error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _enhance_prompt_with_strategy(
        self,
        agent_config: Dict[str, Any],
        strategy: str,
        error_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance agent prompt based on retry strategy"""
        
        enhanced = agent_config.copy()
        base_prompt = enhanced["detailed_prompt"]
        
        if strategy == "normal":
            # No enhancement for first attempt
            return enhanced
        
        elif strategy == "fix_obvious":
            # Add error context and common fixes
            if error_history:
                enhancement = f"""

🔧 PREVIOUS ATTEMPT FAILED
Error: {error_history[-1]['error'][:300]}

COMMON FIXES TO TRY:
1. Check all imports are correct
2. Verify file paths are absolute (/app/data/uploads/...)
3. Ensure variables are defined before use
4. Check for syntax errors
5. Validate function calls and parameters

FIX THE ISSUE AND TRY AGAIN:
"""
                enhanced["detailed_prompt"] = base_prompt + enhancement
        
        elif strategy == "web_search":
            # Search for solution and add to prompt
            if error_history:
                solution = await self._search_for_solution(error_history[-1]["error"])
                enhancement = f"""

🌐 WEB SEARCH SOLUTION:

{solution}

PREVIOUS ERROR:
{error_history[-1]['error'][:300]}

APPLY THE WEB SEARCH SOLUTION TO FIX THIS ERROR:
"""
                enhanced["detailed_prompt"] = base_prompt + enhancement
        
        elif strategy == "rewrite":
            # Force complete rewrite
            errors_summary = self._summarize_errors(error_history)
            enhancement = f"""

🔄 COMPLETE REWRITE REQUIRED

All previous attempts failed. Start from scratch with a fresh approach.

ERRORS TO AVOID:
{errors_summary}

CRITICAL REQUIREMENTS:
1. Write COMPLETE working code (not partial)
2. Include ALL imports at the top
3. Use ABSOLUTE paths: /app/data/uploads/filename
4. Add proper error handling
5. Test each step
6. Return ACTUAL results (not descriptions)

START FRESH - WRITE THE COMPLETE SOLUTION:
"""
            enhanced["detailed_prompt"] = base_prompt + enhancement
        
        else:  # alternative
            # Try completely different approach
            errors_summary = self._summarize_errors(error_history)
            enhancement = f"""

🎯 ALTERNATIVE APPROACH REQUIRED

All previous methods failed. Use a COMPLETELY DIFFERENT approach.

FAILED APPROACHES:
{errors_summary}

NEW STRATEGY OPTIONS:
1. Use different library/tool if possible
2. Break task into smaller steps
3. Simplify the approach
4. Use alternative file formats
5. Try different vector DB or method

IMPLEMENT A COMPLETELY DIFFERENT SOLUTION:
"""
            enhanced["detailed_prompt"] = base_prompt + enhancement
        
        return enhanced
    
    async def _search_for_solution(self, error_message: str) -> str:
        """Search web for error solution using WebSearch tool"""
        
        try:
            from ..tools.predefined.web_search_tool import WebSearchTool
            
            # Extract error type
            error_type = error_message.split(':')[0] if ':' in error_message else error_message[:100]
            
            # Build search query
            query = f"python {error_type} solution fix"
            
            print(f"      🌐 Searching web for: {query}")
            
            # Get credentials
            credentials = await self.credential_manager.get_credential("system", "tavily")
            
            if not credentials:
                return "⚠️ Web search unavailable (no Tavily API key). Add TAVILY_API_KEY to credentials."
            
            # Execute search
            search_tool = WebSearchTool()
            result = await search_tool.safe_execute(
                inputs={
                    "query": query,
                    "max_results": 3,
                    "search_depth": "basic"
                },
                credentials=credentials
            )
            
            if result.success:
                output = result.output
                solution_parts = []
                
                if output.get("answer"):
                    solution_parts.append(f"DIRECT ANSWER:\n{output['answer']}\n")
                
                solution_parts.append("TOP SOLUTIONS:")
                for idx, res in enumerate(output.get("results", [])[:3], 1):
                    solution_parts.append(f"\n{idx}. {res['title']}")
                    solution_parts.append(f"   Source: {res['url']}")
                    solution_parts.append(f"   {res['content'][:250]}...")
                
                print(f"      ✅ Found {len(output.get('results', []))} solutions")
                return "\n".join(solution_parts)
            else:
                return f"⚠️ Web search failed: {result.error}"
                
        except Exception as e:
            return f"⚠️ Could not search for solution: {str(e)}"
    
    def _summarize_errors(self, error_history: List[Dict[str, Any]]) -> str:
        """Create concise summary of all errors"""
        
        if not error_history:
            return "No previous errors"
        
        summary = []
        for entry in error_history:
            error_preview = entry['error'][:150].replace('\n', ' ')
            summary.append(f"• Attempt {entry['attempt']} ({entry['strategy']}): {error_preview}")
        
        return "\n".join(summary)
    
    async def _provision_tools(
        self,
        agent_id: str,
        required_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Provision tools for agent
        
        Strategy:
        1. Check if tool is predefined (use that)
        2. Otherwise, provision dynamically
        """
        provisioned = []
        
        # ALWAYS add code execution first
        provisioned.append({
            "type": "code_execution",
            "tool_name": "python_executor",
            "sandbox": True
        })
        
        for tool_req in required_tools:
            try:
                tool_name = tool_req.get("name", "")
                
                # Check if it's a predefined tool
                if self._is_predefined_tool(tool_name):
                    provisioned.append({
                        "type": "predefined",
                        "tool_name": tool_name,
                        "spec": tool_req
                    })
                else:
                    # Use existing provisioning logic
                    tool_config = await self.tool_registry.provision_tool(
                        tool_name=tool_name,
                        agent_id=agent_id,
                        purpose=tool_req.get("purpose", "task")
                    )
                    tool_config["spec"] = tool_req
                    provisioned.append(tool_config)
                    
            except Exception as e:
                print(f"     ⚠️  Failed to provision {tool_req.get('name')}: {e}")
        
        return provisioned
    
    def _is_predefined_tool(self, tool_name: str) -> bool:
        """Check if tool is predefined"""
        predefined_tools = [
            "rag_builder",
            "rag_chat",
            "report_generator",
            "web_search"
        ]
        return tool_name.lower() in predefined_tools
    
    async def _get_tool_credentials(
        self,
        user_id: str,
        provisioned_tools: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, str]]:
        """Get credentials for all tools"""
        
        credentials = {}
        
        for tool in provisioned_tools:
            tool_name = tool.get("tool_name", "")
            
            # Map tool to service name
            service_mapping = {
                "rag_builder": "openai",
                "rag_chat": "openai",
                "web_search": "tavily"
            }
            
            service_name = service_mapping.get(tool_name)
            if service_name:
                creds = await self.credential_manager.get_credential(user_id, service_name)
                if creds:
                    credentials[tool_name] = creds
        
        return credentials
    
    async def _create_langchain_tools(
        self,
        provisioned_tools: List[Dict[str, Any]],
        credentials: Dict[str, Dict[str, str]]
    ) -> List[Tool]:
        """Create LangChain tools from provisioned tools"""
        
        tools = []
        
        # ✅ FIX: Get OpenAI credentials from settings
        openai_creds = {"openai_api_key": settings.OPENAI_API_KEY}
        
        for prov_tool in provisioned_tools:
            try:
                tool_type = prov_tool.get("type")
                tool_name = prov_tool.get("tool_name", "")
                
                if tool_type == "predefined":
                    # ✅ FIX: Pass OpenAI credentials
                    tool = await self._create_predefined_tool(tool_name, openai_creds)
                    if tool:
                        tools.append(tool)
                        print(f"     ✅ Added predefined: {tool_name}")
                
                elif tool_type == "code_execution":
                    from ..tools.tool_implementations.code_executor_tools import create_code_executor_tool
                    code_tool = create_code_executor_tool()
                    tools.append(code_tool)
                    print(f"     ✅ Added: execute_python")
                
                elif tool_type == "vector_db":
                    from ..tools.tool_implementations.vector_db_tools import create_vector_db_tools
                    vector_tools = await create_vector_db_tools(prov_tool)
                    tools.extend(vector_tools)
                    print(f"     ✅ Added: vector_db tools")
                
                elif tool_type == "mcp" and prov_tool.get("available"):
                    from ..tools.tool_implementations.mcp_tools import create_mcp_tools
                    mcp_tools = await create_mcp_tools(prov_tool["client"])
                    tools.extend(mcp_tools)
                    print(f"     ✅ Added: {prov_tool['mcp_name']}")
            
            except Exception as e:
                print(f"     ⚠️  Error creating tool: {e}")
        
        # Add service deployment tools
        try:
            from ..tools.tool_implementations.service_deployment_tools import create_service_deployment_tools
            service_tools = create_service_deployment_tools()
            tools.extend(service_tools)
            print(f"     ✅ Added: service_deployment tools")
        except Exception as e:
            print(f"     ⚠️  Service tools error: {e}")
        
        return tools
    
    async def _create_predefined_tool(
        self,
        tool_name: str,
        credentials: Optional[Dict[str, str]]
    ) -> Optional[Tool]:
        """Create instance of predefined tool"""
        
        try:
            if not credentials:
                credentials = {}
            if "openai_api_key" not in credentials:
                credentials["openai_api_key"] = settings.OPENAI_API_KEY

            if tool_name == "rag_builder":
                from ..tools.predefined.rag_builder_tool import RagBuilderTool
                tool = RagBuilderTool()
                return tool.to_langchain_tool()
            
            elif tool_name == "rag_chat":
                from ..tools.predefined.rag_chat_tool import RagChatTool
                tool = RagChatTool()
                return tool.to_langchain_tool()
            
            elif tool_name == "report_generator":
                from ..tools.predefined.report_generator_tool import ReportGeneratorTool
                tool = ReportGeneratorTool()
                return tool.to_langchain_tool()
            
            elif tool_name == "web_search":
                from ..tools.predefined.web_search_tool import WebSearchTool
                tool = WebSearchTool()
                return tool.to_langchain_tool()
            
        except Exception as e:
            print(f"     ⚠️  Could not create {tool_name}: {e}")
        
        return None
    
    async def _execute_with_tools(
        self,
        llm: ChatOpenAI,
        tools: List[Tool],
        agent_config: Dict[str, Any],
        agent_input: str
    ) -> str:
        """Execute with LangChain tools"""
        
        try:
            from langchain_classic.agents import AgentExecutor, create_react_agent
            from langchain_core.prompts import PromptTemplate
            
            # INTELLIGENT REACT TEMPLATE
            react_template = """You are an AI agent with specialized tools.

    {custom_instructions}

    ═══════════════════════════════════════════════════════════════════════════════
    🎯 CRITICAL: HOW TO USE TOOLS CORRECTLY
    ═══════════════════════════════════════════════════════════════════════════════

    YOU HAVE TWO TYPES OF TOOLS:

    1️⃣  execute_python:
    • Runs Python code in isolation
    • Input: Python code as string
    • Output: Text/string
    • NO MEMORY between calls
    
    2️⃣  Predefined tools (rag_builder, rag_chat, deploy_streamlit):
    • Input: JSON like {{"param": "value"}}
    • Output: JSON result
    • Built-in validation and credentials

    ═══════════════════════════════════════════════════════════════════════════════
    ❌ WHAT DOESN'T WORK (COMMON MISTAKES)
    ═══════════════════════════════════════════════════════════════════════════════

    ❌ DON'T import tools:
    from rag_builder import index  ← WRONG! Not a Python module!

    ❌ DON'T pass variable names:
    Action: rag_builder
    Action Input: my_data  ← WRONG! Variable doesn't exist in tool!

    ❌ DON'T expect shared state:
    Call 1: data = load()
    Call 2: process(data)  ← WRONG! 'data' doesn't exist!

    ═══════════════════════════════════════════════════════════════════════════════
    ✅ CORRECT PATTERNS
    ═══════════════════════════════════════════════════════════════════════════════

    PATTERN 1: Direct tool call (when you have all inputs)
    ────────────────────────────────────────────────────────────────────
    Thought: I have the file path, I'll index directly
    Action: rag_builder
    Action Input: {{"file_paths": ["/app/data/uploads/file.xlsx"], "vector_db": "chromadb"}}

    Observation: {{"status": "success", "total_chunks": 45}}


    PATTERN 2: Python prep + tool (when you need to prepare data first)
    ────────────────────────────────────────────────────────────────────
    Thought: I need to check the file first
    Action: execute_python
    Action Input:
    import pandas as pd
    import json
    df = pd.read_excel('/app/data/uploads/file.xlsx')
    # Prepare JSON for next tool
    result = {{"file_paths": ["/app/data/uploads/file.xlsx"]}}
    print(json.dumps(result))

    Observation: {{"file_paths": ["/app/data/uploads/file.xlsx"]}}

    Thought: Now I'll use that JSON to call rag_builder
    Action: rag_builder
    Action Input: {{"file_paths": ["/app/data/uploads/file.xlsx"], "vector_db": "chromadb"}}


    PATTERN 3: Complex logic all in Python
    ────────────────────────────────────────────────────────────────────
    Thought: Complex processing, I'll do it all in one call
    Action: execute_python
    Action Input:
    import pandas as pd
    df = pd.read_excel('/app/data/uploads/file.xlsx')
    processed = df.dropna()
    processed.to_csv('/app/data/uploads/output.csv')
    print(f"Saved {{len(processed)}} rows")

    ═══════════════════════════════════════════════════════════════════════════════
    📋 TOOL REFERENCE
    ═══════════════════════════════════════════════════════════════════════════════

    execute_python:
    Input: Python code (string)
    Example: import pandas as pd\\ndf = pd.read_csv('file.csv')\\nprint(len(df))

    rag_builder:
    Input: {{"file_paths": ["/path/to/file"], "vector_db": "chromadb"}}
    Output: {{"status": "success", "total_chunks": 45}}

    rag_chat:
    Input: {{"query": "What is X?", "collection_name": "my_docs"}}
    Output: {{"answer": "...", "sources": [...]}}

    deploy_streamlit:
    Input: Complete Streamlit app code (string)
    Output: URL where deployed

    ═══════════════════════════════════════════════════════════════════════════════

    AVAILABLE TOOLS:
    {tools}

    USE THIS EXACT FORMAT:

    Thought: [Your reasoning - which tool to use and why]
    Action: [Exactly one of: {tool_names}]
    Action Input: [For execute_python: code. For others: JSON]
    Observation: [Tool output appears here]
    ... (Repeat Thought/Action/Input/Observation as needed)
    Thought: I now know the final answer
    Final Answer: [Complete answer to user]

    BEGIN!

    Question: {input}
    Thought:{agent_scratchpad}"""
            
            prompt = PromptTemplate(
                template=react_template,
                input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
                partial_variables={
                    "custom_instructions": agent_config["detailed_prompt"]
                }
            )
            
            # Create agent
            agent = create_react_agent(llm, tools, prompt)
            
            # Create executor - REMOVED invalid early_stopping_method
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=20,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            # Execute
            result = await executor.ainvoke({"input": agent_input})
            
            # Check intermediate steps
            if "intermediate_steps" in result:
                print(f"\n   📊 Intermediate steps: {len(result['intermediate_steps'])}")
                for i, (action, observation) in enumerate(result['intermediate_steps'], 1):
                    print(f"      Step {i}: {action.tool} - {str(observation)[:100]}...")
            
            return result.get("output", str(result))
            
        except Exception as e:
            print(f"   ⚠️  Tool execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to direct LLM
            print(f"   🔄 Falling back to direct LLM execution...")
            return await self._execute_without_tools(llm, agent_config, agent_input)
        
    async def _execute_without_tools(
        self,
        llm: ChatOpenAI,
        agent_config: Dict[str, Any],
        agent_input: str
    ) -> str:
        """Direct LLM execution without tools"""
        
        from langchain_core.messages import SystemMessage, HumanMessage
        
        print(f"\n   📝 Executing with direct LLM (no tools)...")
        
        messages = [
            SystemMessage(content=agent_config["detailed_prompt"]),
            HumanMessage(content=agent_input)
        ]
        
        response = await llm.ainvoke(messages)
        return response.content
        
    def _prepare_comprehensive_input(
        self,
        agent_config: Dict[str, Any],
        input_data: Any
    ) -> str:
        """Prepare comprehensive input for agent"""
        
        parts = [f"TASK: {agent_config.get('task', 'Execute task')}"]
        
        # Add file context
        if isinstance(input_data, dict) and "files" in input_data:
            files = input_data["files"]
            if files:
                parts.append("\nAVAILABLE FILES:")
                for file_info in files:
                    parts.append(f"\n  File: {file_info['filename']}")
                    parts.append(f"    Path: {file_info['path']}")
                    parts.append(f"    Type: {file_info['type']}")
        
        # Add previous agent outputs
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                if key.startswith("input_from_"):
                    agent_name = key.replace("input_from_", "")
                    parts.append(f"\nINPUT FROM {agent_name.upper()}:")
                    parts.append(json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))
        
        # Simple input
        if isinstance(input_data, str):
            parts.append(f"\nINPUT: {input_data}")
        
        return "\n".join(parts)
    
    def _parse_output(self, output: str) -> Any:
        """Parse output intelligently"""
        
        if not isinstance(output, str):
            return output
        
        output_stripped = output.strip()
        
        # Try JSON
        if output_stripped.startswith('{') or output_stripped.startswith('['):
            try:
                return json.loads(output_stripped)
            except json.JSONDecodeError:
                pass
        
        # Try JSON from markdown
        if '```json' in output_stripped:
            try:
                json_start = output_stripped.index('```json') + 7
                json_end = output_stripped.index('```', json_start)
                json_str = output_stripped[json_start:json_end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass
        
        return output
    
    def _is_execution_successful(self, result: Dict[str, Any]) -> bool:
        """Determine if execution was actually successful"""
        
        output = str(result.get("output", ""))
        output_lower = output.lower()
        
        # Signs agent just described what to do (FAILURE)
        description_phrases = [
            "here's what you should do",
            "you should",
            "steps to follow",
            "you need to",
            "first you would",
            "the process involves",
            "here's how to"
        ]
        
        # Signs of actual execution (SUCCESS)
        execution_signs = [
            "indexed",
            "created",
            "deployed",
            "processed",
            "generated",
            "saved",
            "completed",
            "✅",
            "success",
            ".png",
            ".pdf",
            ".docx",
            "/app/data/uploads"
        ]
        
        has_description = any(phrase in output_lower for phrase in description_phrases)
        has_execution = any(sign in output_lower for sign in execution_signs)
        
        # Success = has execution signs WITHOUT description phrases
        return has_execution and not has_description