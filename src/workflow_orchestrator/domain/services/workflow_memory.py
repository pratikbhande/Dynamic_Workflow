"""Workflow Memory - Intelligent workflow reuse"""
from typing import Dict, Any, Optional, List
import json
from ...infrastructure.llm.openai_client import OpenAIClient
from ...infrastructure.vector_stores.factory import VectorStoreFactory
from ...infrastructure.database.mongodb import get_mongodb


class WorkflowMemory:
    """Manages workflow memory for intelligent reuse"""
    
    def __init__(self):
        self.embeddings_client = OpenAIClient()
        self.vector_store = VectorStoreFactory.create("chromadb")
        self.collection_name = "workflow_memory"
        self.similarity_threshold = 0.85
        self._initialized = False
    
    async def initialize(self):
        """Initialize the workflow memory collection"""
        if not self._initialized:
            try:
                # Create collection if doesn't exist
                self.collection_name = await self.vector_store.create_collection(
                    name=self.collection_name,
                    dimension=1536
                )
                self._initialized = True
            except Exception as e:
                # Collection might already exist
                self._initialized = True
                print(f"Workflow memory collection ready: {e}")
    
    async def find_similar_workflow(
        self,
        task_description: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar workflow from memory
        
        Returns:
            Workflow dict if found, None otherwise
        """
        await self.initialize()
        
        try:
            # Generate embedding for task
            task_embedding = await self.embeddings_client.get_embedding(task_description)
            
            # Search in vector store
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_embedding=task_embedding,
                top_k=3
            )
            
            if not results:
                return None
            
            # Check if top result is similar enough
            top_result = results[0]
            similarity = 1 - top_result['distance']  # Convert distance to similarity
            
            print(f"🔍 Workflow similarity: {similarity:.2%}")
            
            if similarity >= self.similarity_threshold:
                # Get full workflow from MongoDB
                workflow_id = top_result['metadata'].get('workflow_id')
                if workflow_id:
                    db = await get_mongodb()
                    workflow = await db.get_collection("workflows").find_one({"id": workflow_id})
                    
                    if workflow and workflow.get('user_id') == user_id:
                        print(f"✅ Reusing workflow: {workflow['name']} (similarity: {similarity:.2%})")
                        return workflow
            
            return None
        
        except Exception as e:
            print(f"⚠️ Error searching workflow memory: {e}")
            return None
    
    async def store_workflow(
        self,
        workflow: Dict[str, Any],
        task_description: str
    ):
        """Store workflow in memory for future reuse"""
        await self.initialize()
        
        try:
            # Generate embedding
            embedding = await self.embeddings_client.get_embedding(task_description)
            
            # Store in vector DB
            await self.vector_store.add_documents(
                collection_name=self.collection_name,
                documents=[task_description],
                embeddings=[embedding],
                metadatas=[{
                    "workflow_id": workflow['id'],
                    "workflow_name": workflow['name'],
                    "user_id": workflow['user_id'],
                    "agent_count": len(workflow.get('agents', []))
                }]
            )
            
            print(f"💾 Stored workflow in memory: {workflow['name']}")
        
        except Exception as e:
            print(f"⚠️ Error storing workflow in memory: {e}")
    
    async def get_workflow_usage_stats(self, workflow_id: str) -> Dict[str, Any]:
        """Get usage statistics for a workflow"""
        db = await get_mongodb()
        
        # Count executions
        execution_count = await db.get_collection("executions").count_documents({
            "workflow_id": workflow_id
        })
        
        # Count successful executions
        success_count = await db.get_collection("executions").count_documents({
            "workflow_id": workflow_id,
            "status": "completed"
        })
        
        return {
            "workflow_id": workflow_id,
            "total_executions": execution_count,
            "successful_executions": success_count,
            "success_rate": success_count / execution_count if execution_count > 0 else 0
        }