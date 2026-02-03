"""RAG Builder Tool - Reliable document indexing"""
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


class RagBuilderTool(BasePredefinedTool):
    """
    RAG Builder Tool - Index documents into vector database
    
    Features:
    - Multiple vector DB support (ChromaDB, FAISS, Pinecone)
    - Automatic chunking
    - Embedding generation
    - Progress tracking
    """
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="rag_builder",
            display_name="RAG Document Indexer",
            description="Index documents into vector database for retrieval-augmented generation",
            category=ToolCategory.RAG,
            tags=["rag", "indexing", "vector-db", "embeddings"]
        )
    
    def get_required_credentials(self) -> List[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="openai_api_key",
                display_name="OpenAI API Key",
                description="API key for generating embeddings",
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
                name="file_paths",
                type="array",
                description="List of file paths to index",
                required=True
            ),
            InputParameter(
                name="vector_db",
                type="string",
                description="Vector database to use",
                required=False,
                default="chromadb",
                options=["chromadb", "faiss", "pinecone"]
            ),
            InputParameter(
                name="collection_name",
                type="string",
                description="Name for the collection",
                required=False,
                default="rag_documents"
            ),
            InputParameter(
                name="chunk_size",
                type="number",
                description="Size of text chunks",
                required=False,
                default=800
            ),
            InputParameter(
                name="chunk_overlap",
                type="number",
                description="Overlap between chunks",
                required=False,
                default=200
            )
        ]
    
    def get_output_schema(self) -> OutputSchema:
        return OutputSchema(
            type="object",
            description="Indexing results",
            properties={
                "collection_name": "Name of created collection",
                "total_chunks": "Number of chunks indexed",
                "total_documents": "Number of documents processed",
                "vector_db": "Vector database used",
                "status": "success or error"
            }
        )
    
    async def execute(
        self,
        inputs: Dict[str, Any],
        credentials: Optional[Dict[str, str]] = None
    ) -> ToolExecutionResult:
        """Execute document indexing"""
        
        try:
            file_paths = inputs["file_paths"]
            vector_db = inputs.get("vector_db", "chromadb")
            collection_name = inputs.get("collection_name", "rag_documents")
            chunk_size = inputs.get("chunk_size", 800)
            chunk_overlap = inputs.get("chunk_overlap", 200)
            
            print(f"\n📚 RAG Builder Starting...")
            print(f"   Files: {len(file_paths)}")
            print(f"   Vector DB: {vector_db}")
            print(f"   Collection: {collection_name}")
            
            # Step 1: Load documents
            documents = await self._load_documents(file_paths)
            print(f"   ✅ Loaded {len(documents)} documents")
            
            # Step 2: Chunk documents
            chunks = self._chunk_documents(documents, chunk_size, chunk_overlap)
            print(f"   ✅ Created {len(chunks)} chunks")
            
            # Step 3: Generate embeddings
            embeddings = await self._generate_embeddings(
                [chunk["text"] for chunk in chunks],
                credentials["openai_api_key"]
            )
            print(f"   ✅ Generated {len(embeddings)} embeddings")
            
            # Step 4: Index into vector DB
            await self._index_to_vector_db(
                vector_db=vector_db,
                collection_name=collection_name,
                chunks=chunks,
                embeddings=embeddings,
                credentials=credentials
            )
            print(f"   ✅ Indexed into {vector_db}")
            
            return ToolExecutionResult(
                success=True,
                output={
                    "collection_name": collection_name,
                    "total_chunks": len(chunks),
                    "total_documents": len(documents),
                    "vector_db": vector_db,
                    "status": "success"
                },
                metadata={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )
            
        except Exception as e:
            import traceback
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"RAG indexing failed: {str(e)}\n{traceback.format_exc()}"
            )
    
    async def _load_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Load documents from file paths"""
        documents = []
        
        for file_path in file_paths:
            try:
                # Determine file type and load appropriately
                if file_path.endswith('.pdf'):
                    content = await self._load_pdf(file_path)
                elif file_path.endswith('.txt'):
                    content = await self._load_txt(file_path)
                elif file_path.endswith('.docx'):
                    content = await self._load_docx(file_path)
                else:
                    # Try as text
                    content = await self._load_txt(file_path)
                
                documents.append({
                    "source": file_path,
                    "content": content
                })
                
            except Exception as e:
                print(f"   ⚠️  Failed to load {file_path}: {e}")
        
        return documents
    
    async def _load_pdf(self, file_path: str) -> str:
        """Load PDF file"""
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text_parts = []
        
        for page in reader.pages:
            text_parts.append(page.extract_text())
        
        return "\n\n".join(text_parts)
    
    async def _load_txt(self, file_path: str) -> str:
        """Load text file"""
        import aiofiles
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def _load_docx(self, file_path: str) -> str:
        """Load DOCX file"""
        from docx import Document
        
        doc = Document(file_path)
        return "\n\n".join([para.text for para in doc.paragraphs])
    
    def _chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Dict[str, Any]]:
        """Chunk documents into smaller pieces"""
        chunks = []
        
        for doc in documents:
            content = doc["content"]
            source = doc["source"]
            
            # Simple chunking by character count
            start = 0
            chunk_id = 0
            
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "chunk_id": chunk_id,
                    "start_char": start,
                    "end_char": end
                })
                
                start += chunk_size - chunk_overlap
                chunk_id += 1
        
        return chunks
    
    async def _generate_embeddings(
        self,
        texts: List[str],
        api_key: str
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Batch process (max 100 at a time)
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _index_to_vector_db(
        self,
        vector_db: str,
        collection_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        credentials: Dict[str, str]
    ):
        """Index chunks into vector database"""
        
        if vector_db == "chromadb":
            await self._index_to_chromadb(collection_name, chunks, embeddings)
        elif vector_db == "faiss":
            await self._index_to_faiss(collection_name, chunks, embeddings)
        elif vector_db == "pinecone":
            await self._index_to_pinecone(
                collection_name,
                chunks,
                embeddings,
                credentials.get("pinecone_api_key")
            )
        else:
            raise ValueError(f"Unsupported vector DB: {vector_db}")
    
    async def _index_to_chromadb(
        self,
        collection_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """Index into ChromaDB"""
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.Client(Settings(
            persist_directory="/app/data/chromadb",
            anonymized_telemetry=False
        ))
        
        # Get or create collection
        try:
            collection = client.get_collection(collection_name)
        except:
            collection = client.create_collection(collection_name)
        
        # Add documents
        collection.add(
            documents=[chunk["text"] for chunk in chunks],
            embeddings=embeddings,
            ids=[f"{chunk['source']}_{chunk['chunk_id']}" for chunk in chunks],
            metadatas=[
                {
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"]
                }
                for chunk in chunks
            ]
        )
    
    async def _index_to_faiss(
        self,
        collection_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """Index into FAISS"""
        import faiss
        import numpy as np
        import pickle
        import os
        
        # Create index
        dimension = len(embeddings[0])
        index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings
        embeddings_array = np.array(embeddings).astype('float32')
        index.add(embeddings_array)
        
        # Save index and metadata
        index_dir = "/app/data/faiss"
        os.makedirs(index_dir, exist_ok=True)
        
        faiss.write_index(index, f"{index_dir}/{collection_name}.index")
        
        with open(f"{index_dir}/{collection_name}.metadata", 'wb') as f:
            pickle.dump(chunks, f)
    
    async def _index_to_pinecone(
        self,
        collection_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        api_key: str
    ):
        """Index into Pinecone"""
        import pinecone
        
        # Initialize Pinecone
        pinecone.init(api_key=api_key)
        
        # Create index if doesn't exist
        if collection_name not in pinecone.list_indexes():
            pinecone.create_index(
                collection_name,
                dimension=len(embeddings[0]),
                metric="cosine"
            )
        
        # Get index
        index = pinecone.Index(collection_name)
        
        # Prepare vectors
        vectors = [
            (
                f"{chunk['source']}_{chunk['chunk_id']}",
                embedding,
                {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"]
                }
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)