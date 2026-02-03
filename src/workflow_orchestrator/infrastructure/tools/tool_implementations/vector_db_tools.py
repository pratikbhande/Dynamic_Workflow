from langchain_core.tools import Tool
from typing import Dict, Any, List
import json
from ...llm.openai_client import OpenAIClient


async def create_vector_db_tools(provisioned_tool: Dict[str, Any]) -> List[Tool]:
    """Create vector DB tools with consistent collection name"""
    
    store = provisioned_tool["store"]
    
    # Use FIXED collection name
    collection_name = "rag_documents"
    
    # Ensure collection exists
    try:
        await store.create_collection(name=collection_name, dimension=1536)
        print(f"     📦 Created collection: {collection_name}")
    except:
        print(f"     📦 Using existing collection: {collection_name}")
    
    embeddings_client = OpenAIClient()
    
    async def add_documents_func(input_str: str) -> str:
        """Add documents to vector database"""
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
            
            return f"SUCCESS: Added {len(documents)} documents to collection '{collection_name}'"
        except Exception as e:
            import traceback
            return f"Error: {str(e)}\n{traceback.format_exc()}"
    
    async def search_documents_func(query: str) -> str:
        """Search vector database"""
        try:
            query_embedding = await embeddings_client.get_embedding(query)
            
            results = await store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=3
            )
            
            if not results:
                return "No results found"
            
            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(f"{i}. {result['document'][:200]}...")
            
            return "Results:\n" + "\n".join(formatted)
        except Exception as e:
            return f"Error: {str(e)}"
    
    return [
        Tool(
            name="add_to_vector_db",
            description='Add documents. Input: {"documents": ["text1", "text2"]}',
            func=lambda x: add_documents_func(x),
            coroutine=add_documents_func
        ),
        Tool(
            name="search_vector_db",
            description="Search documents. Input: query text",
            func=lambda x: search_documents_func(x),
            coroutine=search_documents_func
        )
    ]