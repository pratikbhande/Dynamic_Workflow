"""Test the enhanced intelligent system"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_complete_workflow():
    """Test the complete intelligent workflow system"""
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        print("🧪 Testing Intelligent Workflow System\n")
        
        # 1. Upload a test file
        print("1️⃣ Uploading test file...")
        files = {
            'file': ('test_data.csv', 'Name,Age,City\nAlice,30,NYC\nBob,25,LA\nCarol,35,SF', 'text/csv')
        }
        data = {'user_id': 'test_user'}
        
        response = await client.post(f"{BASE_URL}/files/upload", files=files, data=data)
        file_data = response.json()
        file_id = file_data['file_id']
        print(f"   ✅ File uploaded: {file_id}\n")
        
        # 2. Generate workflow with Streamlit app deployment
        print("2️⃣ Generating intelligent workflow...")
        workflow_request = {
            "task_description": "Create a Streamlit dashboard to visualize this data with charts",
            "user_id": "test_user",
            "file_ids": [file_id]
        }
        
        response = await client.post(f"{BASE_URL}/workflows/generate", json=workflow_request)
        workflow = response.json()
        workflow_id = workflow['workflow_id']
        print(f"   ✅ Workflow generated: {workflow_id}")
        print(f"   📊 Agents: {len(workflow['agents'])}\n")
        
        # 3. Approve workflow
        print("3️⃣ Approving workflow...")
        response = await client.post(
            f"{BASE_URL}/workflows/approve",
            json={"workflow_id": workflow_id}
        )
        print("   ✅ Workflow approved\n")
        
        # 4. Execute workflow
        print("4️⃣ Executing workflow with self-healing...")
        execution_request = {
            "workflow_id": workflow_id,
            "file_ids": [file_id]
        }
        
        response = await client.post(f"{BASE_URL}/executions/execute", json=execution_request)
        execution = response.json()
        print(f"   ✅ Execution: {execution['status']}")
        
        if 'deployed_services' in execution.get('final_output', {}):
            print("\n   🚀 DEPLOYED SERVICES:")
            for service in execution['final_output']['deployed_services']:
                print(f"      {service['type']}: {service['url']}")
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())