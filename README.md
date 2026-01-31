# Workflow Orchestrator - POC

Dynamic Multi-Agent Workflow System that generates and executes AI agent workflows.

## Features

- 🤖 Dynamic workflow generation using GPT-4
- 🔧 Agent-selected tools (ChromaDB, FAISS, code execution)
- 🎯 Automatic prompt generation for each agent
- 📊 Vector database provisioning on-demand
- 🔄 Sequential workflow execution

## Setup

### 1. Install Dependencies
```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### 2. Setup MongoDB
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 4. Run the Application
```bash
poetry run python -m workflow_orchestrator.main
```

Or with uvicorn:
```bash
poetry run uvicorn workflow_orchestrator.main:app --reload
```

## Usage

### 1. Generate a Workflow
```bash
curl -X POST http://localhost:8000/workflows/generate \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build a RAG system for my PDF documents",
    "data_inventory": {
      "files": ["document1.pdf", "document2.pdf"]
    },
    "user_id": "user_123"
  }'
```

### 2. Approve Workflow
```bash
curl -X POST http://localhost:8000/workflows/approve \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "wf_abc123"
  }'
```

### 3. Execute Workflow
```bash
curl -X POST http://localhost:8000/executions/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "wf_abc123",
    "user_data": {
      "query": "What is the main topic of these documents?"
    }
  }'
```

## API Endpoints

- `POST /workflows/generate` - Generate workflow
- `GET /workflows/{workflow_id}` - Get workflow details
- `POST /workflows/approve` - Approve workflow
- `GET /workflows/user/{user_id}` - List user workflows
- `POST /executions/execute` - Execute workflow
- `GET /executions/{execution_id}` - Get execution details

## Architecture
```
Domain Layer (Business Logic)
  ├── Workflow Generator
  └── Models

Application Layer (Use Cases)
  ├── Workflow Service
  └── Execution Service

Infrastructure Layer (External)
  ├── Vector Stores (ChromaDB, FAISS)
  ├── LLM Client (OpenAI)
  ├── Tools Registry
  └── Agent Executor

API Layer (FastAPI)
  ├── Routes
  └── Schemas
```

## Example Workflows

### RAG System
```json
{
  "task_description": "Create a RAG system that indexes my documents and answers questions",
  "data_inventory": {
    "files": ["doc1.pdf", "doc2.pdf"]
  }
}
```

### Data Analysis
```json
{
  "task_description": "Analyze sales data and generate insights",
  "data_inventory": {
    "files": ["sales_2024.csv"]
  }
}
```

### Code Generator
```json
{
  "task_description": "Generate Python code to process CSV files",
  "data_inventory": {
    "requirements": "Read CSV, clean data, export to JSON"
  }
}
```