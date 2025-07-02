# FastAPI + Jinja Integration Guide

This guide shows how to integrate the OpenAI Agentic Workflow System into a FastAPI web application with Jinja2 templates.

## 🏗️ Project Structure

```
your-fastapi-project/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── routers/
│   │   ├── __init__.py
│   │   └── agents.py          # Agent routes
│   ├── templates/             # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── query.html
│   │   └── results.html
│   ├── static/               # CSS, JS, images
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── models/
│       └── schemas.py        # Pydantic models
├── agents/                   # Your agent system
│   ├── __init__.py
│   ├── base_agent.py
│   ├── web_search_agent.py
│   ├── file_search_agent.py
│   ├── input_interpreter_agent.py
│   ├── handoff_agent.py
│   └── workflow_coordinator.py
├── requirements.txt
├── .env
└── main.py                  # Entry point
```

## 📦 Dependencies

Add these to your `requirements.txt`:

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
jinja2>=3.1.2
python-multipart>=0.0.6
aiofiles>=23.2.1
python-dotenv>=1.0.0
openai>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pydantic>=2.0.0
aiohttp>=3.9.0
rich>=13.0.0
```

## 🔧 FastAPI Application Setup

### 1. Main Application (`app/main.py`)

```python
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.routers import agents
from agents import WorkflowCoordinator

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Agent Workflow System",
    description="Multi-agent AI system with web interface",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])

# Initialize global workflow coordinator
workflow_coordinator = None

@app.on_event("startup")
async def startup_event():
    """Initialize the workflow coordinator on startup"""
    global workflow_coordinator
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Initialize with custom search directories
    search_directories = [
        ".",
        "./app",
        "./agents",
        # Add more directories as needed
    ]
    workflow_coordinator = WorkflowCoordinator(search_directories=search_directories)
    print("✅ Workflow Coordinator initialized")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with query form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agents": "initialized" if workflow_coordinator else "not_initialized"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

### 2. Agent Router (`app/routers/agents.py`)

```python
from fastapi import APIRouter, HTTPException, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime

from app.models.schemas import QueryRequest, QueryResponse, WorkflowStatus
from app.main import workflow_coordinator

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Store active workflows (in production, use Redis or database)
active_workflows: Dict[str, Dict[str, Any]] = {}

@router.post("/query", response_model=QueryResponse)
async def process_query(query_request: QueryRequest):
    """Process a query through the agent workflow"""
    
    if not workflow_coordinator:
        raise HTTPException(status_code=500, detail="Workflow coordinator not initialized")
    
    try:
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Store workflow status
        active_workflows[workflow_id] = {
            "status": "processing",
            "query": query_request.query,
            "started_at": datetime.now().isoformat(),
            "result": None
        }
        
        # Process the query
        result = await workflow_coordinator.process_query(
            query_request.query,
            query_request.options
        )
        
        # Update workflow status
        active_workflows[workflow_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": result
        })
        
        return QueryResponse(
            workflow_id=workflow_id,
            status="completed",
            result=result
        )
        
    except Exception as e:
        # Update workflow with error
        if workflow_id in active_workflows:
            active_workflows[workflow_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            })
        
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.post("/query/async")
async def process_query_async(
    query_request: QueryRequest,
    background_tasks: BackgroundTasks
):
    """Start async query processing"""
    
    workflow_id = str(uuid.uuid4())
    
    # Store initial workflow status
    active_workflows[workflow_id] = {
        "status": "queued",
        "query": query_request.query,
        "created_at": datetime.now().isoformat()
    }
    
    # Add background task
    background_tasks.add_task(
        process_query_background,
        workflow_id,
        query_request.query,
        query_request.options
    )
    
    return {
        "workflow_id": workflow_id,
        "status": "queued",
        "message": "Query queued for processing"
    }

async def process_query_background(workflow_id: str, query: str, options: Optional[Dict] = None):
    """Background task to process query"""
    try:
        # Update status
        active_workflows[workflow_id].update({
            "status": "processing",
            "started_at": datetime.now().isoformat()
        })
        
        # Process query
        result = await workflow_coordinator.process_query(query, options)
        
        # Update with result
        active_workflows[workflow_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": result
        })
        
    except Exception as e:
        active_workflows[workflow_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })

@router.get("/workflow/{workflow_id}/status", response_model=WorkflowStatus)
async def get_workflow_status(workflow_id: str):
    """Get the status of a workflow"""
    
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_data = active_workflows[workflow_id]
    
    return WorkflowStatus(
        workflow_id=workflow_id,
        status=workflow_data["status"],
        query=workflow_data["query"],
        created_at=workflow_data.get("created_at"),
        started_at=workflow_data.get("started_at"),
        completed_at=workflow_data.get("completed_at"),
        failed_at=workflow_data.get("failed_at"),
        result=workflow_data.get("result"),
        error=workflow_data.get("error")
    )

@router.get("/capabilities")
async def get_agent_capabilities():
    """Get capabilities of all agents"""
    
    if not workflow_coordinator:
        raise HTTPException(status_code=500, detail="Workflow coordinator not initialized")
    
    capabilities = {}
    
    # Get capabilities from each agent
    agents = [
        ("input_interpreter", workflow_coordinator.input_interpreter),
        ("web_search", workflow_coordinator.web_search_agent),
        ("file_search", workflow_coordinator.file_search_agent),
        ("handoff", workflow_coordinator.handoff_agent)
    ]
    
    for agent_name, agent in agents:
        try:
            agent_capabilities = await agent.get_capabilities()
            capabilities[agent_name] = agent_capabilities
        except Exception as e:
            capabilities[agent_name] = {"error": str(e)}
    
    return capabilities

# Web interface routes
@router.get("/web/query", response_class=HTMLResponse)
async def query_form(request: Request):
    """Display query form"""
    return templates.TemplateResponse("query.html", {"request": request})

@router.post("/web/query", response_class=HTMLResponse)
async def submit_query(
    request: Request,
    query: str = Form(...),
    search_scope: str = Form("both"),
    execution_mode: str = Form("auto")
):
    """Handle form submission and display results"""
    
    try:
        # Prepare query options
        options = {
            "scope": search_scope,
            "execution_mode": execution_mode
        }
        
        # Process query
        result = await workflow_coordinator.process_query(query, options)
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "query": query,
            "result": result,
            "success": True
        })
        
    except Exception as e:
        return templates.TemplateResponse("results.html", {
            "request": request,
            "query": query,
            "error": str(e),
            "success": False
        })

@router.get("/web/async-query", response_class=HTMLResponse)
async def async_query_form(request: Request):
    """Display async query form"""
    return templates.TemplateResponse("async_query.html", {"request": request})

@router.post("/web/async-query", response_class=HTMLResponse)
async def submit_async_query(
    request: Request,
    query: str = Form(...),
    search_scope: str = Form("both")
):
    """Submit async query and redirect to status page"""
    
    workflow_id = str(uuid.uuid4())
    
    # Store workflow
    active_workflows[workflow_id] = {
        "status": "queued",
        "query": query,
        "created_at": datetime.now().isoformat()
    }
    
    # Start background processing
    asyncio.create_task(process_query_background(
        workflow_id, 
        query, 
        {"scope": search_scope}
    ))
    
    return templates.TemplateResponse("workflow_status.html", {
        "request": request,
        "workflow_id": workflow_id,
        "query": query
    })

@router.get("/web/workflow/{workflow_id}", response_class=HTMLResponse)
async def workflow_status_page(request: Request, workflow_id: str):
    """Display workflow status page"""
    
    if workflow_id not in active_workflows:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Workflow not found"
        })
    
    workflow_data = active_workflows[workflow_id]
    
    return templates.TemplateResponse("workflow_status.html", {
        "request": request,
        "workflow_id": workflow_id,
        "workflow_data": workflow_data
    })
```

### 3. Pydantic Models (`app/models/schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The query to process")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Additional options for query processing")

class QueryResponse(BaseModel):
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class WorkflowStatus(BaseModel):
    workflow_id: str
    status: str  # queued, processing, completed, failed
    query: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AgentCapabilities(BaseModel):
    agent_name: str
    capabilities: List[str]
    description: str

class SessionStats(BaseModel):
    total_queries: int
    intent_distribution: Dict[str, int]
    agent_usage: Dict[str, int]
    avg_agents_per_query: float
```

## 🎨 Jinja2 Templates

### 1. Base Template (`app/templates/base.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Agent Workflow System{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="{{ url_for('static', path='/css/styles.css') }}" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot me-2"></i>
                AI Agent System
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">
                            <i class="fas fa-home me-1"></i>Home
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/api/agents/web/query">
                            <i class="fas fa-search me-1"></i>Query
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/api/agents/web/async-query">
                            <i class="fas fa-clock me-1"></i>Async Query
                        </a>
                    </li>
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/docs" target="_blank">
                            <i class="fas fa-book me-1"></i>API Docs
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container my-4">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-light py-4 mt-5">
        <div class="container text-center">
            <p class="mb-0">
                <i class="fas fa-heart text-danger"></i>
                Built with FastAPI, Jinja2 & OpenAI GPT-4
            </p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', path='/js/app.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 2. Home Page (`app/templates/index.html`)

```html
{% extends "base.html" %}

{% block title %}Home - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto">
        <!-- Hero Section -->
        <div class="text-center mb-5">
            <h1 class="display-4 mb-3">
                <i class="fas fa-robot text-primary"></i>
                AI Agent Workflow System
            </h1>
            <p class="lead">
                Intelligent multi-agent system that combines web search, file analysis, 
                and workflow coordination to provide comprehensive responses to your queries.
            </p>
        </div>

        <!-- Quick Start -->
        <div class="card mb-4">
            <div class="card-header">
                <h3 class="card-title mb-0">
                    <i class="fas fa-rocket me-2"></i>Quick Start
                </h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <a href="/api/agents/web/query" class="btn btn-primary btn-lg w-100">
                            <i class="fas fa-search me-2"></i>
                            Ask a Question
                        </a>
                        <small class="text-muted d-block mt-2">
                            Get immediate results from our AI agents
                        </small>
                    </div>
                    <div class="col-md-6 mb-3">
                        <a href="/api/agents/web/async-query" class="btn btn-outline-primary btn-lg w-100">
                            <i class="fas fa-clock me-2"></i>
                            Async Query
                        </a>
                        <small class="text-muted d-block mt-2">
                            Submit long-running queries with status tracking
                        </small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Agent Capabilities -->
        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="card h-100 text-center">
                    <div class="card-body">
                        <i class="fas fa-brain fa-3x text-primary mb-3"></i>
                        <h5 class="card-title">Input Interpreter</h5>
                        <p class="card-text">Analyzes and understands your queries</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card h-100 text-center">
                    <div class="card-body">
                        <i class="fas fa-globe fa-3x text-success mb-3"></i>
                        <h5 class="card-title">Web Search</h5>
                        <p class="card-text">Searches the internet for information</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card h-100 text-center">
                    <div class="card-body">
                        <i class="fas fa-file-search fa-3x text-warning mb-3"></i>
                        <h5 class="card-title">File Search</h5>
                        <p class="card-text">Analyzes local files and code</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="card h-100 text-center">
                    <div class="card-body">
                        <i class="fas fa-cogs fa-3x text-info mb-3"></i>
                        <h5 class="card-title">Coordinator</h5>
                        <p class="card-text">Orchestrates agent workflows</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Example Queries -->
        <div class="card">
            <div class="card-header">
                <h3 class="card-title mb-0">
                    <i class="fas fa-lightbulb me-2"></i>Example Queries
                </h3>
            </div>
            <div class="card-body">
                <div class="list-group list-group-flush">
                    <div class="list-group-item border-0 px-0">
                        <strong>Research & Analysis:</strong>
                        "What are the latest developments in AI and find any AI-related files in this project"
                    </div>
                    <div class="list-group-item border-0 px-0">
                        <strong>Code Discovery:</strong>
                        "Find all Python files related to data processing and explain what they do"
                    </div>
                    <div class="list-group-item border-0 px-0">
                        <strong>Web Research:</strong>
                        "Search for recent breakthroughs in quantum computing"
                    </div>
                    <div class="list-group-item border-0 px-0">
                        <strong>File Analysis:</strong>
                        "Analyze all configuration files and summarize the project setup"
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 3. Query Form (`app/templates/query.html`)

```html
{% extends "base.html" %}

{% block title %}Query - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto">
        <div class="card">
            <div class="card-header">
                <h2 class="card-title mb-0">
                    <i class="fas fa-search me-2"></i>Ask the AI Agents
                </h2>
            </div>
            <div class="card-body">
                <form method="post" action="/api/agents/web/query">
                    <div class="mb-3">
                        <label for="query" class="form-label">Your Query</label>
                        <textarea 
                            class="form-control" 
                            id="query" 
                            name="query" 
                            rows="4" 
                            required
                            placeholder="Ask anything... The AI agents will determine the best approach to answer your question."
                        ></textarea>
                        <div class="form-text">
                            Be as specific or general as you like. The system will interpret your intent and coordinate the appropriate agents.
                        </div>
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label for="search_scope" class="form-label">Search Scope</label>
                            <select class="form-select" id="search_scope" name="search_scope">
                                <option value="both" selected>Both Web & Local Files</option>
                                <option value="web">Web Search Only</option>
                                <option value="local">Local Files Only</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="execution_mode" class="form-label">Execution Mode</label>
                            <select class="form-select" id="execution_mode" name="execution_mode">
                                <option value="auto" selected>Automatic</option>
                                <option value="parallel">Parallel Execution</option>
                                <option value="sequential">Sequential Execution</option>
                            </select>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between">
                        <a href="/" class="btn btn-outline-secondary">
                            <i class="fas fa-arrow-left me-1"></i>Back to Home
                        </a>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-paper-plane me-1"></i>Submit Query
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Example Queries -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-lightbulb me-2"></i>Quick Examples
                </h5>
            </div>
            <div class="card-body">
                <div class="d-flex flex-wrap gap-2">
                    <button class="btn btn-outline-info btn-sm" onclick="setQuery('What is machine learning?')">
                        What is machine learning?
                    </button>
                    <button class="btn btn-outline-info btn-sm" onclick="setQuery('Find all Python files in this project')">
                        Find Python files
                    </button>
                    <button class="btn btn-outline-info btn-sm" onclick="setQuery('Latest AI news and local AI code')">
                        AI research + code
                    </button>
                    <button class="btn btn-outline-info btn-sm" onclick="setQuery('Analyze project configuration')">
                        Project analysis
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function setQuery(query) {
    document.getElementById('query').value = query;
}
</script>
{% endblock %}
```

### 4. Results Page (`app/templates/results.html`)

```html
{% extends "base.html" %}

{% block title %}Query Results - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <!-- Query Display -->
        <div class="card mb-4">
            <div class="card-header">
                <h3 class="card-title mb-0">
                    <i class="fas fa-question-circle me-2"></i>Your Query
                </h3>
            </div>
            <div class="card-body">
                <blockquote class="blockquote mb-0">
                    <p>"{{ query }}"</p>
                </blockquote>
            </div>
        </div>

        {% if success %}
            <!-- Final Response -->
            <div class="card mb-4">
                <div class="card-header bg-success text-white">
                    <h3 class="card-title mb-0">
                        <i class="fas fa-check-circle me-2"></i>AI Response
                    </h3>
                </div>
                <div class="card-body">
                    <div class="response-content">
                        {{ result.final_response | replace('\n', '<br>') | safe }}
                    </div>
                </div>
            </div>

            <!-- Agent Results -->
            {% if result.agent_results %}
            <div class="card mb-4">
                <div class="card-header">
                    <h4 class="card-title mb-0">
                        <i class="fas fa-robot me-2"></i>Agent Results
                    </h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        {% for agent_name, agent_result in result.agent_results.items() %}
                        <div class="col-md-6 mb-3">
                            <div class="card h-100">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        {% if agent_name == "WebSearchAgent" %}
                                            <i class="fas fa-globe text-success me-1"></i>
                                        {% elif agent_name == "FileSearchAgent" %}
                                            <i class="fas fa-file-search text-warning me-1"></i>
                                        {% elif agent_name == "InputInterpreterAgent" %}
                                            <i class="fas fa-brain text-primary me-1"></i>
                                        {% else %}
                                            <i class="fas fa-cog text-info me-1"></i>
                                        {% endif %}
                                        {{ agent_name.replace('Agent', '') }}
                                    </h6>
                                </div>
                                <div class="card-body">
                                    {% if agent_result.error %}
                                        <div class="alert alert-warning mb-0">
                                            <i class="fas fa-exclamation-triangle me-1"></i>
                                            {{ agent_result.error }}
                                        </div>
                                    {% else %}
                                        {% if agent_name == "WebSearchAgent" %}
                                            <p><strong>Sources Found:</strong> {{ agent_result.source_count }}</p>
                                            <p><strong>Summary:</strong></p>
                                            <div class="text-muted">{{ agent_result.summary[:200] }}...</div>
                                        {% elif agent_name == "FileSearchAgent" %}
                                            <p><strong>Files Found:</strong> {{ agent_result.files_found }}</p>
                                            <p><strong>Analysis:</strong></p>
                                            <div class="text-muted">{{ agent_result.analysis[:200] }}...</div>
                                        {% elif agent_name == "InputInterpreterAgent" %}
                                            <p><strong>Intent:</strong> {{ agent_result.primary_intent }}</p>
                                            <p><strong>Scope:</strong> {{ agent_result.scope }}</p>
                                            <p><strong>Confidence:</strong> {{ (agent_result.confidence * 100) | round }}%</p>
                                        {% else %}
                                            <div class="text-muted">Workflow coordination completed</div>
                                        {% endif %}
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            {% endif %}

            <!-- Workflow Details -->
            {% if result.execution_plan %}
            <div class="card mb-4">
                <div class="card-header">
                    <h4 class="card-title mb-0">
                        <i class="fas fa-project-diagram me-2"></i>Execution Details
                    </h4>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <strong>Strategy:</strong> {{ result.execution_plan.execution_strategy | title }}
                        </div>
                        <div class="col-md-4">
                            <strong>Coordination:</strong> {{ result.execution_plan.coordination_strategy | title }}
                        </div>
                        <div class="col-md-4">
                            <strong>Duration:</strong> {{ result.execution_plan.estimated_duration | title }}
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}

        {% else %}
            <!-- Error Display -->
            <div class="card mb-4">
                <div class="card-header bg-danger text-white">
                    <h3 class="card-title mb-0">
                        <i class="fas fa-exclamation-triangle me-2"></i>Error
                    </h3>
                </div>
                <div class="card-body">
                    <div class="alert alert-danger mb-0">
                        {{ error }}
                    </div>
                </div>
            </div>
        {% endif %}

        <!-- Actions -->
        <div class="d-flex justify-content-between">
            <a href="/api/agents/web/query" class="btn btn-primary">
                <i class="fas fa-plus me-1"></i>New Query
            </a>
            <a href="/" class="btn btn-outline-secondary">
                <i class="fas fa-home me-1"></i>Back to Home
            </a>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_css %}
<style>
.response-content {
    font-size: 1.1rem;
    line-height: 1.6;
    white-space: pre-line;
}

.card-header h6 {
    font-weight: 600;
}

.text-muted {
    font-size: 0.9rem;
}
</style>
{% endblock %}
```

## 📱 JavaScript Integration (`app/static/js/app.js`)

```javascript
// Async query status polling
function pollWorkflowStatus(workflowId) {
    const statusElement = document.getElementById('workflow-status');
    const resultElement = document.getElementById('workflow-result');
    
    const poll = async () => {
        try {
            const response = await fetch(`/api/agents/workflow/${workflowId}/status`);
            const data = await response.json();
            
            // Update status
            statusElement.innerHTML = `
                <div class="alert alert-${getStatusColor(data.status)}">
                    <i class="fas fa-${getStatusIcon(data.status)} me-1"></i>
                    Status: ${data.status.toUpperCase()}
                </div>
            `;
            
            if (data.status === 'completed') {
                // Display results
                displayResults(data.result);
                return; // Stop polling
            } else if (data.status === 'failed') {
                // Display error
                resultElement.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        Error: ${data.error}
                    </div>
                `;
                return; // Stop polling
            }
            
            // Continue polling
            setTimeout(poll, 2000);
            
        } catch (error) {
            console.error('Polling error:', error);
            statusElement.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    Failed to get status updates
                </div>
            `;
        }
    };
    
    poll();
}

function getStatusColor(status) {
    switch (status) {
        case 'completed': return 'success';
        case 'failed': return 'danger';
        case 'processing': return 'warning';
        default: return 'info';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'completed': return 'check-circle';
        case 'failed': return 'exclamation-triangle';
        case 'processing': return 'spinner fa-spin';
        default: return 'clock';
    }
}

function displayResults(result) {
    const resultElement = document.getElementById('workflow-result');
    
    resultElement.innerHTML = `
        <div class="card">
            <div class="card-header bg-success text-white">
                <h4 class="mb-0">
                    <i class="fas fa-check-circle me-2"></i>Results
                </h4>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <h5>Final Response:</h5>
                    <div class="p-3 bg-light rounded">
                        ${result.final_response.replace(/\n/g, '<br>')}
                    </div>
                </div>
                
                <div class="mt-3">
                    <h5>Agent Summary:</h5>
                    <div class="row">
                        ${Object.entries(result.agent_results || {}).map(([agent, data]) => `
                            <div class="col-md-6 mb-2">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">${agent.replace('Agent', '')}</h6>
                                        <p class="card-text">
                                            ${data.error ? 
                                                `<span class="text-danger">Error: ${data.error}</span>` :
                                                '<span class="text-success">✓ Completed</span>'
                                            }
                                        </p>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="mt-3">
                    <a href="/api/agents/web/query" class="btn btn-primary">
                        <i class="fas fa-plus me-1"></i>New Query
                    </a>
                </div>
            </div>
        </div>
    `;
}

// Form enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
    
    // Example query buttons
    window.setQuery = function(query) {
        const queryInput = document.getElementById('query');
        if (queryInput) {
            queryInput.value = query;
            queryInput.style.height = 'auto';
            queryInput.style.height = queryInput.scrollHeight + 'px';
        }
    };
});
```

## 🚀 Usage Examples

### 1. Simple API Call

```python
import httpx
import asyncio

async def call_agent_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/agents/query",
            json={
                "query": "What is FastAPI and find any FastAPI files in this project",
                "options": {"scope": "both"}
            }
        )
        return response.json()

# Usage
result = asyncio.run(call_agent_api())
print(result["result"]["final_response"])
```

### 2. Using in FastAPI Route

```python
from fastapi import FastAPI, Depends
from agents import WorkflowCoordinator

app = FastAPI()

# Dependency to get coordinator
def get_coordinator():
    return WorkflowCoordinator()

@app.post("/custom-analysis")
async def custom_analysis(
    data: dict,
    coordinator: WorkflowCoordinator = Depends(get_coordinator)
):
    # Custom processing
    query = f"Analyze this data: {data}"
    
    result = await coordinator.process_query(query)
    
    return {
        "analysis": result["final_response"],
        "agents_used": list(result["agent_results"].keys())
    }
```

### 3. Background Task Integration

```python
from fastapi import BackgroundTasks
import uuid

workflows = {}

@app.post("/process-document")
async def process_document(
    document_path: str,
    background_tasks: BackgroundTasks
):
    workflow_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        process_document_task,
        workflow_id,
        document_path
    )
    
    return {"workflow_id": workflow_id}

async def process_document_task(workflow_id: str, document_path: str):
    coordinator = WorkflowCoordinator()
    
    query = f"Analyze the document at {document_path} and summarize its content"
    
    try:
        result = await coordinator.process_query(query)
        workflows[workflow_id] = {"status": "completed", "result": result}
    except Exception as e:
        workflows[workflow_id] = {"status": "failed", "error": str(e)}
```

## 🔧 Deployment

### 1. Using Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Using Gunicorn

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📝 Best Practices

1. **Error Handling**: Always wrap agent calls in try-catch blocks
2. **Async Operations**: Use background tasks for long-running queries
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Caching**: Cache frequently used agent responses
5. **Monitoring**: Log agent performance and errors
6. **Security**: Validate inputs and sanitize outputs
7. **Testing**: Write tests for your agent integrations

This integration provides a complete web interface for your AI agent system with both synchronous and asynchronous query processing capabilities.