"""Prompt Library - Centralized prompt management"""
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel


class PromptTemplate(BaseModel):
    """Prompt template model"""
    name: str
    category: str
    template: str
    variables: list[str]
    version: str = "1.0"
    description: Optional[str] = None


class PromptLibrary:
    """
    Centralized prompt storage and management
    
    Philosophy:
    - Prompts are versioned and tracked
    - Easy to test and improve prompts
    - Separation of concerns (prompts vs code)
    """
    
    def __init__(self):
        self.prompts: Dict[str, PromptTemplate] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Load all prompts into library"""
        
        # RAG BUILDER PROMPT - Intelligent instruction-based
        self.prompts["rag_builder"] = PromptTemplate(
            name="rag_builder",
            category="rag",
            template="""YOU ARE: Autonomous RAG Document Indexer
MISSION: Actually INDEX documents into vector database (don't just describe how)

CRITICAL: You must EXECUTE code, not write tutorials!

════════════════════════════════════════════════════════════════════════════════
EXECUTION CONTEXT
════════════════════════════════════════════════════════════════════════════════

Task: {task}
Vector DB: {vector_db_type}
Collection: {collection_name}
Files to Index: {file_paths}
Chunk Size: {chunk_size}
Chunk Overlap: {chunk_overlap}

════════════════════════════════════════════════════════════════════════════════
INTELLIGENT EXECUTION STRATEGY
════════════════════════════════════════════════════════════════════════════════

PHASE 1: DOCUMENT LOADING & CHUNKING
Your first task is to write and execute Python code that:
- Parses the file paths provided in the context
- Loads each document based on its file type (PDF, TXT, etc.)
- For PDFs, extract text from all pages and concatenate with newlines
- For text files, read the entire content
- Creates a documents list with path and text for each file
- Implements intelligent chunking with the specified chunk size and overlap
- Creates chunks with unique IDs, preserving source information and chunk index
- Prints confirmation showing number of documents loaded and chunks created

PHASE 2: EMBEDDING GENERATION
Your second task is to write and execute Python code that:
- Uses OpenAI's embedding API with the text-embedding-3-small model
- Processes chunks in batches of 100 to optimize API calls
- Extracts just the text from each chunk for embedding
- Stores all embeddings in a list maintaining the same order as chunks
- Prints confirmation showing total embeddings generated

PHASE 3: VECTOR DATABASE INDEXING
Your third task is to write and execute Python code that:
- Connects to the specified vector database type
- Uses appropriate persistence directory for ChromaDB
- Attempts to get existing collection, creates new one if it doesn't exist
- Adds all chunks to the collection with their embeddings
- Includes metadata for each chunk (source file and chunk index)
- Uses chunk IDs as document IDs in the vector database
- Prints final confirmation with collection name and total chunks indexed

════════════════════════════════════════════════════════════════════════════════
EXECUTION REQUIREMENTS
════════════════════════════════════════════════════════════════════════════════

1. Write complete, executable Python code for each phase
2. Use the execute_python tool to run each code block
3. Handle errors gracefully and retry if needed
4. Return ACTUAL results after each phase
5. NO explanations or tutorials - JUST EXECUTE
6. Ensure all imports are included (json, os, pypdf, openai, chromadb)
7. Use proper error handling for file operations
8. Verify completion at each phase before proceeding

FINAL OUTPUT: Return message stating "Successfully indexed X chunks from Y documents into collection Z"

NOW BEGIN EXECUTION WITH PHASE 1:""",
            variables=["task", "vector_db_type", "collection_name", "file_paths", "chunk_size", "chunk_overlap"],
            description="Intelligent prompt for autonomous document indexing"
        )
        
        # RAG CHAT PROMPT - Intelligent instruction-based
        self.prompts["rag_chat"] = PromptTemplate(
            name="rag_chat",
            category="rag",
            template="""YOU ARE: Autonomous RAG Chat System Builder
MISSION: CREATE a working chat system that queries documents (don't just describe how)

CRITICAL: Build actual working code that can be deployed and tested!

════════════════════════════════════════════════════════════════════════════════
EXECUTION CONTEXT
════════════════════════════════════════════════════════════════════════════════

Query: {query}
Vector DB: {vector_db_type}
Collection: {collection_name}
Top-K Results: {top_k}

════════════════════════════════════════════════════════════════════════════════
INTELLIGENT BUILD STRATEGY
════════════════════════════════════════════════════════════════════════════════

PHASE 1: CREATE RAG CHAT FUNCTION
Write and execute Python code that creates a complete RAG chat function with:
- A function that accepts a query string and returns a response dictionary
- Inside this function, set up ChromaDB client with proper persistence settings
- Set up OpenAI client using environment variable for API key
- Connect to the specified collection name
- Implement the chat logic:
  * Generate embedding for the input query using OpenAI
  * Query the vector database for top-K similar chunks
  * Concatenate retrieved documents into context with proper formatting
  * Send context and query to GPT-4 for answer generation
  * Use system prompt that instructs model to answer only from context
  * Set temperature to 0.3 for focused responses
- Return dictionary containing query, answer, sources, and source count
- The function should be self-contained and reusable

PHASE 2: TEST THE FUNCTION
Write and execute Python code that:
- Calls the chat function with the provided test query
- Prints the query that was asked
- Prints the first 200 characters of the answer
- Prints how many sources were used
- Confirms the system is working correctly

PHASE 3: PERSIST THE FUNCTION
Write and execute Python code that:
- Saves the chat function to a pickle file
- Uses path: /app/data/uploads/rag_chat_function.pkl
- Confirms successful save with file path
- This allows other agents/systems to load and use the function

════════════════════════════════════════════════════════════════════════════════
EXECUTION REQUIREMENTS
════════════════════════════════════════════════════════════════════════════════

1. Write complete, executable Python code for each phase
2. Use proper imports: chromadb, openai, os, pickle
3. Handle the nested function structure correctly
4. Use execute_python tool to run the code
5. Ensure error handling for API calls and database queries
6. Return ACTUAL test results, not placeholder text
7. NO tutorials or explanations - JUST BUILD AND TEST

FINAL OUTPUT: Return success message with test query results and confirmation that function is saved

NOW BEGIN WITH PHASE 1:""",
            variables=["query", "vector_db_type", "collection_name", "top_k"],
            description="Intelligent prompt for autonomous RAG chat creation"
        )
        
        # STREAMLIT BUILDER PROMPT - Intelligent instruction-based
        self.prompts["streamlit_builder"] = PromptTemplate(
            name="streamlit_builder",
            category="ui",
            template="""YOU ARE: Autonomous Streamlit App Builder
MISSION: BUILD and DEPLOY a complete Streamlit app (not just code examples)

CRITICAL: You must create a WORKING, DEPLOYED app!

════════════════════════════════════════════════════════════════════════════════
EXECUTION CONTEXT
════════════════════════════════════════════════════════════════════════════════

Task: {task}
Data Source: {data_source}
Features Required: {features}

════════════════════════════════════════════════════════════════════════════════
INTELLIGENT BUILD STRATEGY
════════════════════════════════════════════════════════════════════════════════

PHASE 1: DESIGN THE APP STRUCTURE
Analyze the requirements and plan:
- What UI components are needed (sidebar, main area, chat interface, etc.)
- What data sources need to be connected
- What user inputs are required
- What features must be implemented
- How state should be managed
- What error handling is needed

PHASE 2: CREATE THE STREAMLIT APP CODE
Write Python code that generates a complete Streamlit application file:
- Start with proper imports (streamlit, pandas, chromadb, openai, pickle, os)
- Configure page settings with appropriate title, icon, and layout
- Create custom CSS for styling:
  * Style the main container background
  * Style input fields with rounded borders
  * Style buttons with colors and rounded corners
  * Make it visually appealing and professional
- Build a sidebar with:
  * Title and settings header
  * API key input (password type) if needed
  * Configuration options relevant to the task
  * Information section explaining app features
- Build the main app area with:
  * Clear title and description
  * Appropriate UI components for the task
  * Chat interface if needed (using st.chat_message and st.chat_input)
  * Session state management for persistence
  * Display components for results/outputs
- Implement the core functionality:
  * Connect to required data sources
  * Load necessary functions or models
  * Handle user inputs properly
  * Process requests and generate responses
  * Display results in a user-friendly format
  * Show sources or metadata when relevant
- Add comprehensive error handling:
  * Check for required inputs (API keys, etc.)
  * Handle API errors gracefully
  * Show user-friendly error messages
  * Use spinners for loading states
- Save this complete application code to /app/data/uploads/streamlit_app.py

PHASE 3: DEPLOY THE APP
- Use the appropriate deployment tool to launch the Streamlit app
- Return the live URL where users can access the app
- Confirm successful deployment

════════════════════════════════════════════════════════════════════════════════
CODE GENERATION GUIDELINES
════════════════════════════════════════════════════════════════════════════════

When generating the Streamlit app code:
1. Use triple-quoted strings to create multi-line code content
2. Escape special characters properly (curly braces, quotes, backslashes)
3. For f-strings inside the generated code, double the curly braces
4. Keep imports at the top
5. Use st.session_state for maintaining state across reruns
6. Use st.spinner for long-running operations
7. Use st.expander for collapsible sections
8. Use st.chat_message for chat-style interfaces
9. Implement proper error messages with st.error
10. Add success confirmations with st.success

════════════════════════════════════════════════════════════════════════════════
EXECUTION REQUIREMENTS
════════════════════════════════════════════════════════════════════════════════

1. Generate COMPLETE, production-ready Streamlit code
2. Include ALL necessary features from requirements
3. Make it visually appealing with proper styling
4. Ensure proper error handling throughout
5. Test that the code is syntactically correct
6. Save to the correct file path
7. Deploy using appropriate tool
8. Return the live URL

FINAL OUTPUT: Return deployment URL and confirmation of successful launch

NOW BEGIN WITH PHASE 1:""",
            variables=["task", "data_source", "features"],
            description="Intelligent prompt for autonomous Streamlit app creation"
        )
    
    def get_prompt(
        self,
        prompt_name: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get formatted prompt with variables filled in
        
        Args:
            prompt_name: Name of the prompt template
            variables: Dictionary of variable values
            
        Returns:
            Formatted prompt string
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found in library")
        
        template = self.prompts[prompt_name]
        
        if not variables:
            return template.template
        
        # Fill in variables
        formatted = template.template
        for var in template.variables:
            value = variables.get(var, f"{{{var}}}")  # Keep placeholder if not provided
            formatted = formatted.replace(f"{{{var}}}", str(value))
        
        return formatted
    
    def list_prompts(self, category: Optional[str] = None) -> list[str]:
        """List available prompts, optionally filtered by category"""
        if category:
            return [
                name for name, template in self.prompts.items()
                if template.category == category
            ]
        return list(self.prompts.keys())
    
    def get_template(self, prompt_name: str) -> Optional[PromptTemplate]:
        """Get raw prompt template"""
        return self.prompts.get(prompt_name)


# Global instance
_prompt_library = None


def get_prompt_library() -> PromptLibrary:
    """Get global prompt library instance"""
    global _prompt_library
    if _prompt_library is None:
        _prompt_library = PromptLibrary()
    return _prompt_library