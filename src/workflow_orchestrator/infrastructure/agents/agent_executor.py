from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
import json

from ..tools.tool_registry import ToolRegistry
from ..tools.tool_implementations.vector_db_tools import create_vector_db_tools
from ..tools.tool_implementations.code_executor_tools import create_code_executor_tool
from ..tools.tool_implementations.file_tools import create_file_tools
from ..tools.tool_implementations.mcp_tools import create_mcp_tools
from ..tools.tool_implementations.service_deployment_tools import create_service_deployment_tools
from ...domain.services.error_memory import ErrorMemory
from ...config import settings


class DynamicAgentExecutor:
    """Executes individual agents with self-healing and error learning"""
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.error_memory = ErrorMemory()
    
    async def execute_agent_with_retry(
        self,
        agent_config: Dict[str, Any],
        input_data: Any,
        max_retries: int = None
    ) -> Dict[str, Any]:
        """Execute agent with automatic retry and self-healing"""
        
        max_retries = max_retries or settings.MAX_RETRY_ATTEMPTS
        last_error = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"\n🔄 Retry attempt {attempt + 1}/{max_retries}")
            
            try:
                result = await self.execute_agent(agent_config, input_data)
                
                # If successful, store the solution if we had previous errors
                if attempt > 0 and last_error:
                    await self.error_memory.store_solution(
                        error_message=last_error,
                        solution=agent_config.get('detailed_prompt', ''),
                        success=True
                    )
                
                return result
            
            except Exception as e:
                last_error = str(e)
                print(f"❌ Agent failed: {last_error}")
                
                if attempt < max_retries - 1:
                    # Try to find solution and enhance prompt
                    enhanced_config = await self._enhance_prompt_with_solution(
                        agent_config, last_error
                    )
                    if enhanced_config:
                        agent_config = enhanced_config
                        print(f"🔧 Applied solution from memory, retrying...")
                    else:
                        print(f"⚠️ No known solution, retrying with web search...")
                        # Enhance with web search if available
                        agent_config = await self._enhance_prompt_with_websearch(
                            agent_config, last_error
                        )
                else:
                    # Final attempt failed
                    return {
                        "agent_id": agent_config["id"],
                        "output": f"Error after {max_retries} attempts: {last_error}",
                        "status": "failed",
                        "error": last_error,
                        "attempts": max_retries
                    }
        
        return {
            "agent_id": agent_config["id"],
            "output": f"Max retries exceeded: {last_error}",
            "status": "failed",
            "error": last_error
        }
    
    async def _enhance_prompt_with_solution(
        self,
        agent_config: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """Enhance agent prompt with known solution"""
        
        if not settings.ENABLE_ERROR_LEARNING:
            return None
        
        # Find solution from memory
        solution = await self.error_memory.find_solution(error_message)
        
        if not solution:
            return None
        
        # Generate error context
        error_context = self.error_memory.generate_error_context(error_message, solution)
        
        # Enhance prompt
        enhanced_config = agent_config.copy()
        enhanced_config['detailed_prompt'] = f"""{agent_config['detailed_prompt']}

{error_context}

⚠️ PREVIOUS ERROR ENCOUNTERED:
{error_message[:300]}

Please apply the suggested solution above to prevent this error.
"""
        
        return enhanced_config
    
    async def _enhance_prompt_with_websearch(
        self,
        agent_config: Dict[str, Any],
        error_message: str
    ) -> Dict[str, Any]:
        """Enhance agent prompt with web search results"""
        
        # Check if websearch MCP is available
        websearch_client = self.tool_registry.mcp_clients.get('websearch')
        if not websearch_client or not websearch_client.connected:
            return agent_config
        
        try:
            # Search for solution
            search_results = await websearch_client.search_solution(error_message)
            
            # Enhance prompt
            enhanced_config = agent_config.copy()
            enhanced_config['detailed_prompt'] = f"""{agent_config['detailed_prompt']}

🔍 WEB SEARCH RESULTS FOR SIMILAR ERROR:
{search_results}

⚠️ PREVIOUS ERROR:
{error_message[:300]}

Use the web search results above to fix this error.
"""
            
            return enhanced_config
        
        except Exception as e:
            print(f"⚠️ Web search failed: {e}")
            return agent_config
    
    async def execute_agent(
        self,
        agent_config: Dict[str, Any],
        input_data: Any
    ) -> Dict[str, Any]:
        """Execute a single agent with full context"""
        
        print(f"\n{'='*60}")
        print(f"🤖 Executing Agent: {agent_config['name']}")
        print(f"   Type: {agent_config['type']}")
        print(f"{'='*60}")
        
        try:
            # 1. Provision tools
            provisioned_tools = await self._provision_tools(
                agent_id=agent_config["id"],
                required_tools=agent_config.get("required_tools", [])
            )
            
            # 2. Create LangChain tools
            langchain_tools = await self._create_langchain_tools(provisioned_tools)
            
            print(f"   Tools available: {len(langchain_tools)}")
            for tool in langchain_tools:
                print(f"     - {tool.name}")
            
            # 3. Prepare comprehensive input
            agent_input = self._prepare_comprehensive_input(agent_config, input_data)
            
            print(f"\n   Input prepared:")
            print(f"     Files: {len(input_data.get('files', []))}")
            
            # 4. Create LLM
            llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4-turbo",
                temperature=0.7
            )
            
            # 5. Execute agent
            if langchain_tools:
                output = await self._execute_with_tools(
                    llm, langchain_tools, agent_config, agent_input
                )
            else:
                output = await self._execute_without_tools(
                    llm, agent_config, agent_input
                )
            
            # 6. Parse output
            parsed_output = self._parse_output(output)
            
            print(f"\n   ✅ Agent completed successfully")
            print(f"   Output preview: {str(parsed_output)[:200]}...")
            
            # 7. Cleanup
            await self.tool_registry.cleanup_tools(provisioned_tools)
            
            return {
                "agent_id": agent_config["id"],
                "output": parsed_output,
                "status": "completed"
            }
            
        except Exception as e:
            print(f"\n   ❌ Agent failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            raise  # Re-raise for retry logic
    
    async def _execute_with_tools(
        self,
        llm: ChatOpenAI,
        tools: List[Tool],
        agent_config: Dict[str, Any],
        agent_input: str
    ) -> str:
        """Execute agent with tools using tool calling"""
        
        print(f"\n   📋 Executing agent with {len(tools)} tools...\n")
        
        # Create simple prompt for tool calling agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", agent_config["detailed_prompt"]),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        try:
            # Try tool calling agent (modern approach)
            agent = create_tool_calling_agent(llm, tools, prompt)
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=15,
                handle_parsing_errors=True
            )
            
            result = await agent_executor.ainvoke({"input": agent_input})
            return result.get("output", str(result))
            
        except Exception as e:
            print(f"   ⚠️  Tool calling failed: {e}")
            print(f"   Falling back to direct LLM with tool descriptions...")
            
            # Fallback: Direct LLM call with tool descriptions
            return await self._execute_with_tool_descriptions(
                llm, tools, agent_config, agent_input
            )
    
    async def _execute_with_tool_descriptions(
        self,
        llm: ChatOpenAI,
        tools: List[Tool],
        agent_config: Dict[str, Any],
        agent_input: str
    ) -> str:
        """Fallback: Execute with tool descriptions but no actual tool calling"""
        
        # Build tool descriptions
        tools_desc = "\n\n".join([
            f"Tool: {tool.name}\nDescription: {tool.description}"
            for tool in tools
        ])
        
        # Create enhanced prompt
        full_prompt = f"""{agent_config["detailed_prompt"]}

AVAILABLE TOOLS:
{tools_desc}

Note: You can reference these tools in your code or response, but execute the logic directly.

INPUT:
{agent_input}

Provide your complete response:
"""
        
        response = await llm.ainvoke([("human", full_prompt)])
        return response.content
    
    async def _execute_without_tools(
        self,
        llm: ChatOpenAI,
        agent_config: Dict[str, Any],
        agent_input: str
    ) -> str:
        """Execute with simple LLM call (no tools)"""
        
        print(f"\n   📋 Executing with LLM (no tools)...\n")
        
        messages = [
            ("system", agent_config["detailed_prompt"]),
            ("human", agent_input)
        ]
        
        response = await llm.ainvoke(messages)
        return response.content
    
    def _parse_output(self, output: str) -> Any:
        """Parse output, try to convert to JSON if possible"""
        
        if not isinstance(output, str):
            return output
        
        output_stripped = output.strip()
        
        # Try to parse as JSON
        if output_stripped.startswith('{') or output_stripped.startswith('['):
            try:
                return json.loads(output_stripped)
            except json.JSONDecodeError:
                pass
        
        # Try to extract JSON from markdown code blocks
        if '```json' in output_stripped:
            try:
                json_start = output_stripped.index('```json') + 7
                json_end = output_stripped.index('```', json_start)
                json_str = output_stripped[json_start:json_end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass
        
        # Try to extract Python code blocks and execute
        if '```python' in output_stripped and 'python_executor' in str(output_stripped):
            try:
                code_start = output_stripped.index('```python') + 9
                code_end = output_stripped.index('```', code_start)
                code = output_stripped[code_start:code_end].strip()
                
                # Execute the code
                print(f"\n   🐍 Executing extracted Python code...")
                from ..tools.tool_implementations.code_executor_tools import create_code_executor_tool
                executor = create_code_executor_tool()
                result = executor.func(code)
                
                # Try to parse result as JSON
                try:
                    return json.loads(result.split("Code executed successfully:\n")[-1])
                except:
                    return result
            except Exception as e:
                print(f"   ⚠️  Code execution failed: {e}")
        
        return output
    
    async def _provision_tools(
        self,
        agent_id: str,
        required_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Provision all required tools for agent"""
        provisioned = []
        
        for tool_req in required_tools:
            try:
                tool_config = await self.tool_registry.provision_tool(
                    tool_name=tool_req["name"],
                    agent_id=agent_id,
                    purpose=tool_req.get("purpose", "task")
                )
                tool_config["spec"] = tool_req
                provisioned.append(tool_config)
                print(f"     ✅ Provisioned: {tool_req['name']}")
            except Exception as e:
                print(f"     ⚠️  Failed to provision {tool_req['name']}: {e}")
        
        return provisioned
    
    async def _create_langchain_tools(
            self,
            provisioned_tools: List[Dict[str, Any]]
        ) -> List[Tool]:
        """Convert provisioned tools to LangChain tools"""
        tools = []
        
        # Add provisioned tools
        for prov_tool in provisioned_tools:
            try:
                if prov_tool["type"] == "vector_db":
                    vector_tools = await create_vector_db_tools(prov_tool)
                    tools.extend(vector_tools)
                    print(f"     ✅ Added vector DB tools: {[t.name for t in vector_tools]}")
                
                elif prov_tool["type"] == "code_execution":
                    code_tool = create_code_executor_tool()
                    tools.append(code_tool)
                    print(f"     ✅ Added code execution tool")
                
                elif prov_tool["type"] == "mcp" and prov_tool.get("available"):
                    mcp_tools = await create_mcp_tools(prov_tool["client"])
                    tools.extend(mcp_tools)
                    print(f"     ✅ Added MCP tools: {[t.name for t in mcp_tools]}")
                
                elif prov_tool.get("spec", {}).get("name") == "filesystem":
                    file_tools = await create_file_tools()
                    tools.extend(file_tools)
                    print(f"     ✅ Added file tools")
            
            except Exception as e:
                print(f"     ⚠️  Error creating tools for {prov_tool.get('type')}: {e}")
        
        # ALWAYS add service deployment tools
        try:
            from ..tools.tool_implementations.service_deployment_tools import create_service_deployment_tools
            service_tools = create_service_deployment_tools()
            tools.extend(service_tools)
            print(f"     ✅ Added service deployment tools: {[t.name for t in service_tools]}")
        except Exception as e:
            print(f"     ⚠️  Error adding service deployment tools: {e}")
        
        # ALWAYS add chat endpoint tools - WITH FIXED ERROR HANDLING
        try:
            from ..tools.tool_implementations.chat_endpoint_tools import create_chat_endpoint_tools
            chat_tools = create_chat_endpoint_tools()
            if chat_tools and isinstance(chat_tools, list):  # Verify it's a list
                tools.extend(chat_tools)
                print(f"     ✅ Added chat endpoint tools: {[t.name for t in chat_tools]}")
            else:
                print(f"     ⚠️  Chat endpoint tools returned invalid type: {type(chat_tools)}")
        except Exception as e:
            import traceback
            print(f"     ⚠️  Error adding chat endpoint tools: {e}")
            print(f"     Traceback: {traceback.format_exc()}")

        return tools
    
    def _prepare_comprehensive_input(
        self,
        agent_config: Dict[str, Any],
        input_data: Any
    ) -> str:
        """Prepare comprehensive input text for agent"""
        
        input_parts = []
        
        # Add task
        input_parts.append(f"TASK: {agent_config.get('task', 'Execute assigned task')}")
        input_parts.append("")
        
        # Add files context if present
        if isinstance(input_data, dict) and "files" in input_data:
            files = input_data["files"]
            if files:
                input_parts.append("AVAILABLE FILES:")
                for file_info in files:
                    input_parts.append(f"\nFile: {file_info['filename']}")
                    input_parts.append(f"  ID: {file_info['file_id']}")
                    input_parts.append(f"  Path: {file_info['path']}")
                    input_parts.append(f"  Type: {file_info['type']}")
                    
                    # Add structured data info for Excel/CSV
                    if 'sheets' in file_info:
                        for sheet_name, sheet_data in file_info['sheets'].items():
                            input_parts.append(f"  Sheet '{sheet_name}':")
                            input_parts.append(f"    Columns: {', '.join(sheet_data['columns'])}")
                            input_parts.append(f"    Sample: {json.dumps(sheet_data['rows'][:2])}")
                    elif 'data' in file_info:
                        input_parts.append(f"  Columns: {', '.join(file_info['data']['columns'])}")
                        input_parts.append(f"  Sample: {json.dumps(file_info['data']['rows'][:2])}")
                
                input_parts.append("")
        
        # Add previous agent outputs
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                if key.startswith("input_from_"):
                    agent_name = key.replace("input_from_", "")
                    input_parts.append(f"INPUT FROM {agent_name.upper()}:")
                    input_parts.append(json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))
                    input_parts.append("")
        
        # If input_data is simple string or dict without special keys
        if isinstance(input_data, str):
            input_parts.append(f"INPUT: {input_data}")
        elif isinstance(input_data, dict) and not any(k in input_data for k in ['files', 'task']):
            input_parts.append("INPUT DATA:")
            input_parts.append(json.dumps(input_data, indent=2))
        
        return "\n".join(input_parts)