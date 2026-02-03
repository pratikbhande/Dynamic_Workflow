"""RAG Chat Tool - Question answering with retrieval"""
from typing import Dict, Any, List, Optional
from ..base_tool import (
    BasePredefinedTool,
    ToolMetadata,
    CredentialRequirement,
    InputParameter,
    OutputSchema,
    ToolExecutionResult,
    ToolCategory
)


class RagChatTool(BasePredefinedTool):
    """
    RAG Chat Tool - Answer questions using indexed documents
    
    Features:
    - Multi-vector DB support
    - Configurable retrieval
    - Source attribution
    - Confidence scoring
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="rag_chat",
            display_name="RAG Chat Assistant",
            description="Answer questions using retrieval-augmented generation from indexed documents",
            category=ToolCategory.RAG,
            tags=["rag", "chat", "qa", "retrieval"]
        )
    
    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="openai_api_key",
                display_name="OpenAI API Key",
                description="API key for embeddings and chat completion",
                required=True,
                secret=True
            ),
            CredentialRequirement(
                key="pinecone_api_key",
                display_name="Pinecone API Key",
                description="Required only if using Pinecone",
                required=False,
                secret=True
            )
        ]
    
    def get_input_parameters(self) -> List[InputParameter]:
        return [
            InputParameter(
                name="query",
                type="string",
                description="User's question",
                required=True
            ),
            InputParameter(
                name="collection_name",
                type="string",
                description="Name of the indexed collection",
                required=True
            ),
            InputParameter(
                name="vector_db",
                type="string",
                description="Vector database to query",
                required=False,
                default="chromadb",
                options=["chromadb", "faiss", "pinecone"]
            ),
            InputParameter(
                name="top_k",
                type="number",
                description="Number of documents to retrieve",
                required=False,
                default=3
            ),
            InputParameter(
                name="system_prompt",
                type="string",
                description="Custom system prompt for the AI",
                required=False,
                default="You are a helpful assistant. Answer based on the provided context only."
            )
        ]
    
    def get_output_schema(self) -> OutputSchema:
        return OutputSchema(
            type="object",
            description="Chat response with sources",
            properties={
                "answer": "Generated answer",
                "sources": "List of source documents",
                "confidence": "Confidence level (high/medium/low)",
                "query": "Original query"
            }
        )
    
    async def execute(
        self,
        inputs: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None
    ) -> ToolExecutionResult:
        """Execute RAG chat query"""
        
        try:
            query = inputs["query"]
            collection_name = inputs["collection_name"]
            vector_db = inputs.get("vector_db", "chromadb")
            top_k = inputs.get("top_k", 3)
            system_prompt = inputs.get("system_prompt", "You are a helpful assistant. Answer based on the provided context only.")
            
            print(f"\n💬 RAG Chat Processing...")
            print(f"   Query: {query[:100]}...")
            print(f"   Collection: {collection_name}")
            print(f"   Vector DB: {vector_db}")
            
            # Step 1: Generate query embedding
            query_embedding = await self._generate_query_embedding(
                query,
                credentials["openai_api_key"]
            )
            print(f"   ✅ Generated query embedding")
            
            # Step 2: Retrieve relevant documents
            retrieved_docs = await self._retrieve_documents(
                vector_db=vector_db,
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k,
                credentials=credentials
            )
            print(f"   ✅ Retrieved {len(retrieved_docs)} documents")
            
            # Step 3: Generate answer
            answer, confidence = await self._generate_answer(
                query=query,
                documents=retrieved_docs,
                system_prompt=system_prompt,
                api_key=credentials["openai_api_key"]
            )
            print(f"   ✅ Generated answer (confidence: {confidence})")
            
            return ToolExecutionResult(
                success=True,
                output={
                    "answer": answer,
                    "sources": [
                        {
                            "text": doc["text"][:200] + "...",
                            "source": doc["metadata"].get("source", "unknown"),
                            "relevance": doc.get("score", 0)
                        }
                        for doc in retrieved_docs
                    ],
                    "confidence": confidence,
                    "query": query
                },
                metadata={
                    "top_k": top_k,
                    "num_sources": len(retrieved_docs)
                }
            )
            
        except Exception as e:
            import traceback
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"RAG chat failed: {str(e)}\n{traceback.format_exc()}"
            )
    
    async def _generate_query_embedding(
        self,
        query: str,
        api_key: str
    ) -> List[float]:
        """Generate embedding for query"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        
        return response.data[0].embedding
    
    async def _retrieve_documents(
        self,
        vector_db: str,
        collection_name: str,
        query_embedding: List[float],
        top_k: int,
        credentials: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents from vector DB"""
        
        if vector_db == "chromadb":
            return await self._retrieve_from_chromadb(collection_name, query_embedding, top_k)
        elif vector_db == "faiss":
            return await self._retrieve_from_faiss(collection_name, query_embedding, top_k)
        elif vector_db == "pinecone":
            return await self._retrieve_from_pinecone(
                collection_name,
                query_embedding,
                top_k,
                credentials.get("pinecone_api_key")
            )
        else:
            raise ValueError(f"Unsupported vector DB: {vector_db}")
    
    async def _retrieve_from_chromadb(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve from ChromaDB"""
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.Client(Settings(
            persist_directory="/app/data/chromadb",
            anonymized_telemetry=False
        ))
        
        collection = client.get_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Format results
        documents = []
        for i in range(len(results['documents'][0])):
            documents.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "score": 1 - results['distances'][0][i]  # Convert distance to similarity
            })
        
        return documents
    
    async def _retrieve_from_faiss(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve from FAISS"""
        import faiss
        import numpy as np
        import pickle
        
        index_dir = "/app/data/faiss"
        
        # Load index
        index = faiss.read_index(f"{index_dir}/{collection_name}.index")
        
        # Load metadata
        with open(f"{index_dir}/{collection_name}.metadata", 'rb') as f:
            chunks = pickle.load(f)
        
        # Search
        query_array = np.array([query_embedding]).astype('float32')
        distances, indices = index.search(query_array, top_k)
        
        # Format results
        documents = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(chunks):
                chunk = chunks[idx]
                documents.append({
                    "text": chunk["text"],
                    "metadata": {
                        "source": chunk["source"],
                        "chunk_id": chunk["chunk_id"]
                    },
                    "score": 1 / (1 + dist)  # Convert distance to similarity
                })
        
        return documents
    
    async def _retrieve_from_pinecone(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int,
        api_key: str
    ) -> List[Dict[str, Any]]:
        """Retrieve from Pinecone"""
        import pinecone
        
        pinecone.init(api_key=api_key)
        index = pinecone.Index(collection_name)
        
        # Query
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        documents = []
        for match in results['matches']:
            documents.append({
                "text": match['metadata']['text'],
                "metadata": {
                    "source": match['metadata'].get('source', 'unknown'),
                    "chunk_id": match['metadata'].get('chunk_id', 0)
                },
                "score": match['score']
            })
        
        return documents
    
    async def _generate_answer(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        system_prompt: str,
        api_key: str
    ) -> tuple[str, str]:
        """
        Generate answer using retrieved documents
        
        Returns:
            (answer, confidence)
        """
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"Document {i}:\n{doc['text']}\n")
        
        context = "\n".join(context_parts)
        
        # Generate answer
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}\n\nProvide a clear answer based on the context above."
                }
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Estimate confidence based on document scores
        avg_score = sum(doc["score"] for doc in documents) / len(documents)
        
        if avg_score > 0.8:
            confidence = "high"
        elif avg_score > 0.5:
            confidence = "medium"
        else:
            confidence = "low"
        
        return answer, confidence