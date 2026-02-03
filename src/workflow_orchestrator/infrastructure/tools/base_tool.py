"""Base Tool Architecture - Foundation for all predefined tools"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict
from pydantic import BaseModel, Field
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories for organization"""
    RAG = "rag"
    REPORT = "report"
    WEB = "web"
    DATA = "data"
    COMMUNICATION = "communication"
    INTEGRATION = "integration"
    CODE = "code"


class CredentialRequirement(BaseModel):
    """Define credential requirements for a tool"""
    key: str
    display_name: str
    description: str
    required: bool = True
    secret: bool = True  # Should be encrypted
    default: Optional[str] = None


class InputParameter(BaseModel):
    """Define input parameter for a tool"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[str]] = None  # For enum-like inputs


class OutputSchema(BaseModel):
    """Define output schema for a tool"""
    type: str
    description: str
    properties: Optional[Dict[str, Any]] = None


class ToolMetadata(BaseModel):
    """Metadata about the tool"""
    name: str
    display_name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "System"
    tags: List[str] = []


class ToolExecutionResult(BaseModel):
    """Result of tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    execution_time: Optional[float] = None


class BasePredefinedTool(ABC):
    """
    Base class for all predefined tools
    
    Design Philosophy:
    - Tools are RELIABLE, tested, maintained
    - Tools handle their own errors gracefully
    - Tools validate inputs before execution
    - Tools provide clear error messages
    - Tools are versioned and documented
    """
    
    def __init__(self):
        self._metadata = self.get_metadata()
        self._credentials = self.get_required_credentials()
        self._inputs = self.get_input_parameters()
        self._output = self.get_output_schema()
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Return tool metadata"""
        pass
    
    @abstractmethod
    def get_required_credentials(self) -> List[CredentialRequirement]:
        """Return required credentials"""
        pass
    
    @abstractmethod
    def get_input_parameters(self) -> List[InputParameter]:
        """Return input parameters"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> OutputSchema:
        """Return output schema"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None
    ) -> ToolExecutionResult:
        """
        Execute the tool
        
        Args:
            inputs: Input parameters
            credentials: Required credentials
            
        Returns:
            ToolExecutionResult with output or error
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate inputs against schema
        
        Returns:
            (is_valid, error_message)
        """
        for param in self._inputs:
            if param.required and param.name not in inputs:
                return False, f"Missing required parameter: {param.name}"
            
            if param.name in inputs:
                value = inputs[param.name]
                
                # Type validation
                if param.type == "string" and not isinstance(value, str):
                    return False, f"{param.name} must be string"
                elif param.type == "number" and not isinstance(value, (int, float)):
                    return False, f"{param.name} must be number"
                elif param.type == "boolean" and not isinstance(value, bool):
                    return False, f"{param.name} must be boolean"
                elif param.type == "array" and not isinstance(value, list):
                    return False, f"{param.name} must be array"
                elif param.type == "object" and not isinstance(value, dict):
                    return False, f"{param.name} must be object"
                
                # Options validation
                if param.options and value not in param.options:
                    return False, f"{param.name} must be one of: {param.options}"
        
        return True, None
    
    def validate_credentials(
        self,
        credentials: Optional[Dict[str, str]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate credentials
        
        Returns:
            (is_valid, error_message)
        """
        required_creds = [c for c in self._credentials if c.required]
        
        if not required_creds:
            return True, None
        
        if not credentials:
            return False, f"Missing required credentials: {[c.key for c in required_creds]}"
        
        for cred in required_creds:
            if cred.key not in credentials:
                return False, f"Missing credential: {cred.display_name}"
        
        return True, None
    
    async def safe_execute(
        self,
        inputs: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None
    ) -> ToolExecutionResult:
        """
        Safe execution with validation and error handling
        """
        import time
        start_time = time.time()
        
        try:
            # Validate inputs
            valid_inputs, input_error = self.validate_inputs(inputs)
            if not valid_inputs:
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Input validation failed: {input_error}"
                )
            
            # Validate credentials
            valid_creds, cred_error = self.validate_credentials(credentials)
            if not valid_creds:
                return ToolExecutionResult(
                    success=False,
                    output=None,
                    error=f"Credential validation failed: {cred_error}"
                )
            
            # Execute
            result = await self.execute(inputs, credentials)
            
            # Add execution time
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Tool execution failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def get_usage_example(self) -> Dict[str, Any]:
        """Return usage example for documentation"""
        example_inputs = {}
        for param in self._inputs:
            if param.default is not None:
                example_inputs[param.name] = param.default
            elif param.type == "string":
                example_inputs[param.name] = f"example_{param.name}"
            elif param.type == "number":
                example_inputs[param.name] = 0
            elif param.type == "boolean":
                example_inputs[param.name] = True
            elif param.type == "array":
                example_inputs[param.name] = []
            elif param.type == "object":
                example_inputs[param.name] = {}
        
        example_credentials = {}
        for cred in self._credentials:
            example_credentials[cred.key] = f"your_{cred.key}"
        
        return {
            "inputs": example_inputs,
            "credentials": example_credentials if example_credentials else None
        }
    
    def to_langchain_tool(self):
        """Convert to LangChain tool format"""
        from langchain_core.tools import Tool
        import json
        import re
        
        async def tool_func(input_str: str) -> str:
            """Tool function for LangChain"""
            try:
                # Parse input flexibly
                if isinstance(input_str, dict):
                    inputs = input_str
                else:
                    input_str = str(input_str).strip()
                    
                    # Try JSON parse
                    try:
                        inputs = json.loads(input_str)
                    except:
                        # Extract JSON from string
                        json_match = re.search(r'\{.*\}', input_str, re.DOTALL)
                        if json_match:
                            try:
                                inputs = json.loads(json_match.group())
                            except:
                                return f"Error: Could not parse input. Expected JSON like {{'param': 'value'}}"
                        else:
                            return f"Error: Input must be JSON. Got: {input_str[:100]}"
                
                credentials = getattr(self, '_credentials', None)

                
                # Execute (no credentials as requested)
                result = await self.safe_execute(inputs, credentials)
                
                if result.success:
                    return json.dumps(result.output, indent=2) if isinstance(result.output, (dict, list)) else str(result.output)
                else:
                    return f"Error: {result.error}"
                    
            except Exception as e:
                import traceback
                return f"Tool execution error: {str(e)}\n{traceback.format_exc()}"
        
        return Tool(
            name=self._metadata.name,
            description=self._metadata.description,
            func=lambda x: tool_func(x),
            coroutine=tool_func
        )