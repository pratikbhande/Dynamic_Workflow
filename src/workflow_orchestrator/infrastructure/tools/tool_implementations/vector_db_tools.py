from langchain.tools import Tool
from typing import Dict, Any, List
import json
from ...llm.openai_client import OpenAIClient

async def create_vector_db_tools(provisioned_tool: Dict[str, Any]) -> List[Tool]:
    """Create LangChain tools for vector DB operations"""
    
    store = provisioned_tool["store"]
    collection_name = provisioned_tool["collection_name"]
    embeddings_client = OpenAIClient()
    
    async def add_documents_func(input_str: str) -> str:
        """Add documents to vector database
        
        Args:
            input_str: JSON string with format: {"documents": ["doc1", "doc2"]}
        """
        try:
            data = json.loads(input_str)
            documents = data.get("documents", [])
            
            if not documents:
                return "Error: No documents provided"
            
            # Generate embeddings
            embeddings = await embeddings_client.get_embeddings(documents)
            
            # Create metadata
            metadatas = [{"text": doc} for doc in documents]
            
            # Add to vector store
            await store.add_documents(
                collection_name=collection_name,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            return f"Successfully added {len(documents)} documents to vector database"
        except Exception as e:
            return f"Error adding documents: {str(e)}"
    
    async def search_documents_func(query: str) -> str:
        """Search for similar documents in vector database
        
        Args:
            query: Search query text
        """
        try:
            # Generate query embedding
            query_embedding = await embeddings_client.get_embedding(query)
            
            # Search
            results = await store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=5
            )
            
            if not results:
                return "No results found"
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. {result['document']} (distance: {result['distance']:.4f})"
                )
            
            return "Search Results:\n" + "\n".join(formatted_results)
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    return [
        Tool(
            name="add_to_vector_db",
            description='Add documents to vector database. Input must be JSON: {"documents": ["text1", "text2"]}',
            func=lambda x: add_documents_func(x),
            coroutine=add_documents_func
        ),
        Tool(
            name="search_vector_db",
            description="Search for similar documents in vector database. Input is the search query text.",
            func=lambda x: search_documents_func(x),
            coroutine=search_documents_func
        )
    ]