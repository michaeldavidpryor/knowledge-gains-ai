# FastAPI + HTMX + DaisyUI Integration Guide

This guide shows how to integrate the OpenAI Agentic Workflow System into a modern FastAPI web application using HTMX for dynamic interactions, DaisyUI for beautiful components, and Tailwind CSS for styling.

## � What's New in This Version

This guide has been completely updated from the previous Bootstrap + JavaScript version to use modern web technologies:

### 🔄 Technology Changes
- **Bootstrap** → **Tailwind CSS + DaisyUI**: Modern utility-first styling with semantic components
- **Vanilla JavaScript** → **HTMX**: Declarative dynamic behavior without complex JavaScript
- **Manual AJAX** → **HTMX Attributes**: Server-side driven interactions
- **Custom Polling** → **HTMX Auto-polling**: Built-in real-time updates

### ✨ Key Improvements
- **Simpler Code**: 80% less JavaScript code to maintain
- **Better Performance**: Server-side rendering with targeted updates
- **Enhanced UX**: Smooth transitions and loading states
- **Progressive Enhancement**: Works without JavaScript enabled
- **Modern Design**: Clean, accessible, and responsive interface
- **Real-time Updates**: Automatic polling for workflow status

### 🎯 New Features
- **Theme Switching**: Light/dark mode toggle
- **Component-based Architecture**: Reusable HTMX components
- **Auto-refreshing Status**: Real-time workflow monitoring
- **Enhanced Error Handling**: Better user feedback
- **Loading States**: Visual feedback during processing

## �🏗️ Project Structure

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

## 🎨 Frontend Stack

- **HTMX**: Dynamic HTML without JavaScript complexity
- **Tailwind CSS**: Utility-first CSS framework
- **DaisyUI**: Beautiful, semantic component library for Tailwind
- **Jinja2**: Server-side templating for dynamic content

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
    """Submit async query and return status component"""
    
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
    
    return templates.TemplateResponse("components/workflow_status.html", {
        "request": request,
        "workflow_id": workflow_id,
        "query": query,
        "workflow_data": active_workflows[workflow_id]
    })

@router.get("/web/workflow/{workflow_id}/status", response_class=HTMLResponse)
async def get_workflow_status_html(request: Request, workflow_id: str):
    """Get workflow status as HTML component for HTMX polling"""
    
    if workflow_id not in active_workflows:
        return templates.TemplateResponse("components/error.html", {
            "request": request,
            "error": "Workflow not found"
        })
    
    workflow_data = active_workflows[workflow_id]
    
    return templates.TemplateResponse("components/workflow_status.html", {
        "request": request,
        "workflow_id": workflow_id,
        "workflow_data": workflow_data
    })

@router.get("/web/workflow/{workflow_id}", response_class=HTMLResponse)
async def workflow_status_page(request: Request, workflow_id: str):
    """Display full workflow status page"""
    
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
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Agent Workflow System{% endblock %}</title>
    
    <!-- Tailwind CSS + DaisyUI -->
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.0/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.6"></script>
    
    <!-- Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    {% block extra_css %}{% endblock %}
</head>
<body class="min-h-screen bg-base-100">
    <!-- Navigation -->
    <div class="navbar bg-primary text-primary-content">
        <div class="navbar-start">
            <div class="dropdown">
                <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16"></path>
                    </svg>
                </div>
                <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 text-base-content">
                    <li><a href="/"><i class="fas fa-home mr-2"></i>Home</a></li>
                    <li><a href="/api/agents/web/query"><i class="fas fa-search mr-2"></i>Query</a></li>
                    <li><a href="/api/agents/web/async-query"><i class="fas fa-clock mr-2"></i>Async Query</a></li>
                </ul>
            </div>
            <a href="/" class="btn btn-ghost text-xl">
                <i class="fas fa-robot mr-2"></i>
                AI Agent System
            </a>
        </div>
        
        <div class="navbar-center hidden lg:flex">
            <ul class="menu menu-horizontal px-1">
                <li><a href="/"><i class="fas fa-home mr-2"></i>Home</a></li>
                <li><a href="/api/agents/web/query"><i class="fas fa-search mr-2"></i>Query</a></li>
                <li><a href="/api/agents/web/async-query"><i class="fas fa-clock mr-2"></i>Async Query</a></li>
            </ul>
        </div>
        
        <div class="navbar-end">
            <div class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn btn-ghost">
                    <i class="fas fa-ellipsis-v"></i>
                </div>
                <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 text-base-content">
                    <li><a href="/docs" target="_blank"><i class="fas fa-book mr-2"></i>API Docs</a></li>
                    <li><a onclick="toggleTheme()"><i class="fas fa-palette mr-2"></i>Toggle Theme</a></li>
                </ul>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8 max-w-7xl">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-200 text-base-content rounded">
        <div class="text-center">
            <p class="font-semibold">
                <i class="fas fa-heart text-red-500 mr-1"></i>
                Built with FastAPI, HTMX, DaisyUI & OpenAI GPT-4
            </p>
        </div>
    </footer>

    <!-- Theme Toggle Script -->
    <script>
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }
        
        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    </script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 2. Home Page (`app/templates/index.html`)

```html
{% extends "base.html" %}

{% block title %}Home - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <!-- Hero Section -->
    <div class="hero min-h-96 bg-gradient-to-r from-primary to-secondary rounded-box mb-8">
        <div class="hero-content text-center text-primary-content">
            <div class="max-w-md">
                <div class="text-6xl mb-4">
                    <i class="fas fa-robot"></i>
                </div>
                <h1 class="text-5xl font-bold">AI Agent Workflow System</h1>
                <p class="py-6 text-lg">
                    Intelligent multi-agent system that combines web search, file analysis, 
                    and workflow coordination to provide comprehensive responses to your queries.
                </p>
                <a href="/api/agents/web/query" class="btn btn-accent btn-lg">
                    <i class="fas fa-rocket mr-2"></i>
                    Get Started
                </a>
            </div>
        </div>
    </div>

    <!-- Quick Start -->
    <div class="card bg-base-100 shadow-xl mb-8">
        <div class="card-body">
            <h2 class="card-title text-2xl mb-4">
                <i class="fas fa-rocket mr-2 text-primary"></i>
                Quick Start
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="card bg-base-200">
                    <div class="card-body text-center">
                        <a href="/api/agents/web/query" class="btn btn-primary btn-lg w-full">
                            <i class="fas fa-search mr-2"></i>
                            Ask a Question
                        </a>
                        <p class="text-sm text-base-content/70 mt-2">
                            Get immediate results from our AI agents
                        </p>
                    </div>
                </div>
                <div class="card bg-base-200">
                    <div class="card-body text-center">
                        <a href="/api/agents/web/async-query" class="btn btn-outline btn-lg w-full">
                            <i class="fas fa-clock mr-2"></i>
                            Async Query
                        </a>
                        <p class="text-sm text-base-content/70 mt-2">
                            Submit long-running queries with status tracking
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Agent Capabilities -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card bg-gradient-to-br from-primary/10 to-primary/20 shadow-lg">
            <div class="card-body text-center">
                <div class="text-4xl text-primary mb-4">
                    <i class="fas fa-brain"></i>
                </div>
                <h3 class="card-title justify-center text-lg">Input Interpreter</h3>
                <p class="text-sm text-base-content/70">
                    Analyzes and understands your queries
                </p>
            </div>
        </div>
        
        <div class="card bg-gradient-to-br from-success/10 to-success/20 shadow-lg">
            <div class="card-body text-center">
                <div class="text-4xl text-success mb-4">
                    <i class="fas fa-globe"></i>
                </div>
                <h3 class="card-title justify-center text-lg">Web Search</h3>
                <p class="text-sm text-base-content/70">
                    Searches the internet for information
                </p>
            </div>
        </div>
        
        <div class="card bg-gradient-to-br from-warning/10 to-warning/20 shadow-lg">
            <div class="card-body text-center">
                <div class="text-4xl text-warning mb-4">
                    <i class="fas fa-file-search"></i>
                </div>
                <h3 class="card-title justify-center text-lg">File Search</h3>
                <p class="text-sm text-base-content/70">
                    Analyzes local files and code
                </p>
            </div>
        </div>
        
        <div class="card bg-gradient-to-br from-info/10 to-info/20 shadow-lg">
            <div class="card-body text-center">
                <div class="text-4xl text-info mb-4">
                    <i class="fas fa-cogs"></i>
                </div>
                <h3 class="card-title justify-center text-lg">Coordinator</h3>
                <p class="text-sm text-base-content/70">
                    Orchestrates agent workflows
                </p>
            </div>
        </div>
    </div>

    <!-- Example Queries -->
    <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
            <h2 class="card-title text-2xl mb-4">
                <i class="fas fa-lightbulb mr-2 text-accent"></i>
                Example Queries
            </h2>
            <div class="space-y-4">
                <div class="alert">
                    <i class="fas fa-search-plus text-primary"></i>
                    <div>
                        <h4 class="font-bold">Research & Analysis</h4>
                        <p class="text-sm">"What are the latest developments in AI and find any AI-related files in this project"</p>
                    </div>
                </div>
                
                <div class="alert">
                    <i class="fas fa-code text-secondary"></i>
                    <div>
                        <h4 class="font-bold">Code Discovery</h4>
                        <p class="text-sm">"Find all Python files related to data processing and explain what they do"</p>
                    </div>
                </div>
                
                <div class="alert">
                    <i class="fas fa-globe text-accent"></i>
                    <div>
                        <h4 class="font-bold">Web Research</h4>
                        <p class="text-sm">"Search for recent breakthroughs in quantum computing"</p>
                    </div>
                </div>
                
                <div class="alert">
                    <i class="fas fa-cog text-info"></i>
                    <div>
                        <h4 class="font-bold">File Analysis</h4>
                        <p class="text-sm">"Analyze all configuration files and summarize the project setup"</p>
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
<div class="max-w-4xl mx-auto">
    <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
            <h1 class="card-title text-3xl mb-6">
                <i class="fas fa-search mr-3 text-primary"></i>
                Ask the AI Agents
            </h1>
            
            <form 
                hx-post="/api/agents/web/query" 
                hx-target="#results-container"
                hx-indicator="#loading-indicator"
                class="space-y-6"
            >
                <!-- Query Input -->
                <div class="form-control">
                    <label class="label">
                        <span class="label-text text-lg font-semibold">Your Query</span>
                    </label>
                    <textarea 
                        class="textarea textarea-bordered h-32 text-base" 
                        id="query" 
                        name="query" 
                        required
                        placeholder="Ask anything... The AI agents will determine the best approach to answer your question."
                    ></textarea>
                    <label class="label">
                        <span class="label-text-alt">
                            Be as specific or general as you like. The system will interpret your intent and coordinate the appropriate agents.
                        </span>
                    </label>
                </div>

                <!-- Options -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="form-control">
                        <label class="label">
                            <span class="label-text font-semibold">Search Scope</span>
                        </label>
                        <select class="select select-bordered" name="search_scope">
                            <option value="both" selected>Both Web & Local Files</option>
                            <option value="web">Web Search Only</option>
                            <option value="local">Local Files Only</option>
                        </select>
                    </div>
                    
                    <div class="form-control">
                        <label class="label">
                            <span class="label-text font-semibold">Execution Mode</span>
                        </label>
                        <select class="select select-bordered" name="execution_mode">
                            <option value="auto" selected>Automatic</option>
                            <option value="parallel">Parallel Execution</option>
                            <option value="sequential">Sequential Execution</option>
                        </select>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="flex flex-col sm:flex-row justify-between items-center gap-4">
                    <a href="/" class="btn btn-outline">
                        <i class="fas fa-arrow-left mr-2"></i>
                        Back to Home
                    </a>
                    
                    <div class="flex gap-2">
                        <button 
                            type="button"
                            hx-post="/api/agents/web/async-query"
                            hx-target="#results-container"
                            hx-indicator="#loading-indicator"
                            class="btn btn-secondary"
                        >
                            <i class="fas fa-clock mr-2"></i>
                            Async Query
                        </button>
                        
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-paper-plane mr-2"></i>
                            Submit Query
                        </button>
                    </div>
                </div>
            </form>
            
            <!-- Loading Indicator -->
            <div id="loading-indicator" class="htmx-indicator mt-6">
                <div class="flex flex-col items-center space-y-4">
                    <span class="loading loading-spinner loading-lg text-primary"></span>
                    <p class="text-lg">Processing your query...</p>
                    <div class="text-sm text-base-content/70">
                        AI agents are analyzing your request and gathering information
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Examples -->
    <div class="card bg-base-100 shadow-xl mt-6">
        <div class="card-body">
            <h2 class="card-title mb-4">
                <i class="fas fa-lightbulb mr-2 text-accent"></i>
                Quick Examples
            </h2>
            <div class="flex flex-wrap gap-2">
                <button 
                    class="btn btn-outline btn-sm" 
                    onclick="setQuery('What is machine learning?')"
                >
                    What is machine learning?
                </button>
                <button 
                    class="btn btn-outline btn-sm" 
                    onclick="setQuery('Find all Python files in this project')"
                >
                    Find Python files
                </button>
                <button 
                    class="btn btn-outline btn-sm" 
                    onclick="setQuery('Latest AI news and local AI code')"
                >
                    AI research + code
                </button>
                <button 
                    class="btn btn-outline btn-sm" 
                    onclick="setQuery('Analyze project configuration')"
                >
                    Project analysis
                </button>
            </div>
        </div>
    </div>

    <!-- Results Container -->
    <div id="results-container" class="mt-6">
        <!-- HTMX will inject results here -->
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function setQuery(query) {
    document.getElementById('query').value = query;
}

// HTMX configuration
document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-Requested-With'] = 'XMLHttpRequest';
});
</script>
{% endblock %}
```

### 4. Async Query Page (`app/templates/async_query.html`)

```html
{% extends "base.html" %}

{% block title %}Async Query - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="max-w-4xl mx-auto">
    <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
            <h1 class="card-title text-3xl mb-6">
                <i class="fas fa-clock mr-3 text-secondary"></i>
                Async Query Processing
            </h1>
            
            <form 
                hx-post="/api/agents/web/async-query" 
                hx-target="#workflow-container"
                hx-indicator="#loading-indicator"
                class="space-y-6"
            >
                <!-- Query Input -->
                <div class="form-control">
                    <label class="label">
                        <span class="label-text text-lg font-semibold">Your Query</span>
                    </label>
                    <textarea 
                        class="textarea textarea-bordered h-32 text-base" 
                        name="query" 
                        required
                        placeholder="Enter your query for background processing..."
                    ></textarea>
                    <label class="label">
                        <span class="label-text-alt">
                            This query will be processed in the background. You can track its progress in real-time.
                        </span>
                    </label>
                </div>

                <!-- Search Scope -->
                <div class="form-control max-w-xs">
                    <label class="label">
                        <span class="label-text font-semibold">Search Scope</span>
                    </label>
                    <select class="select select-bordered" name="search_scope">
                        <option value="both" selected>Both Web & Local Files</option>
                        <option value="web">Web Search Only</option>
                        <option value="local">Local Files Only</option>
                    </select>
                </div>

                <!-- Submit Button -->
                <div class="flex gap-4">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-paper-plane mr-2"></i>
                        Start Processing
                    </button>
                    <a href="/" class="btn btn-outline">
                        <i class="fas fa-arrow-left mr-2"></i>
                        Back to Home
                    </a>
                </div>
            </form>
            
            <!-- Loading Indicator -->
            <div id="loading-indicator" class="htmx-indicator mt-6">
                <div class="flex flex-col items-center space-y-4">
                    <span class="loading loading-spinner loading-lg text-secondary"></span>
                    <p class="text-lg">Starting workflow...</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Workflow Status Container -->
    <div id="workflow-container" class="mt-6">
        <!-- HTMX will inject workflow status here -->
    </div>
</div>
{% endblock %}
```

### 5. Results Page (Simplified - HTMX handles most logic via components)

```html
{% extends "base.html" %}

{% block title %}Query Results - AI Agent Workflow System{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto">
    <!-- This template now primarily uses the results component -->
    <!-- The actual results are rendered by components/results.html -->
    
    {% include 'components/results.html' %}
</div>
{% endblock %}
```

## 🔧 Updated FastAPI Route Handlers

Since we're using HTMX, the route handlers need to return the component templates:

```python
@router.post("/web/query", response_class=HTMLResponse)
async def submit_query(
    request: Request,
    query: str = Form(...),
    search_scope: str = Form("both"),
    execution_mode: str = Form("auto")
):
    """Handle form submission and return results component"""
    
    try:
        # Prepare query options
        options = {
            "scope": search_scope,
            "execution_mode": execution_mode
        }
        
        # Process query
        result = await workflow_coordinator.process_query(query, options)
        
        return templates.TemplateResponse("components/results.html", {
            "request": request,
            "query": query,
            "result": result,
            "success": True
        })
        
    except Exception as e:
        return templates.TemplateResponse("components/results.html", {
            "request": request,
            "query": query,
            "error": str(e),
            "success": False
        })
```

## 🎨 HTMX Component Templates

### 1. Workflow Status Component (`app/templates/components/workflow_status.html`)

```html
<div class="card bg-base-100 shadow-xl">
    <div class="card-body">
        <h2 class="card-title mb-4">
            <i class="fas fa-cog mr-2 text-primary"></i>
            Workflow Status
        </h2>
        
        <div class="mb-4">
            <div class="text-sm text-base-content/70 mb-2">Query:</div>
            <div class="p-4 bg-base-200 rounded-lg">
                "{{ workflow_data.query }}"
            </div>
        </div>
        
        <!-- Status Indicator -->
        <div class="mb-6">
            {% if workflow_data.status == 'queued' %}
                <div class="alert alert-info">
                    <i class="fas fa-clock mr-2"></i>
                    <span>Queued - Waiting to start processing</span>
                </div>
            {% elif workflow_data.status == 'processing' %}
                <div class="alert alert-warning">
                    <span class="loading loading-spinner loading-sm mr-2"></span>
                    <span>Processing - AI agents are working on your query</span>
                </div>
            {% elif workflow_data.status == 'completed' %}
                <div class="alert alert-success">
                    <i class="fas fa-check-circle mr-2"></i>
                    <span>Completed - Results are ready!</span>
                </div>
            {% elif workflow_data.status == 'failed' %}
                <div class="alert alert-error">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    <span>Failed - {{ workflow_data.get('error', 'Unknown error occurred') }}</span>
                </div>
            {% endif %}
        </div>
        
        <!-- Auto-refresh for active workflows -->
        {% if workflow_data.status in ['queued', 'processing'] %}
            <div 
                hx-get="/api/agents/web/workflow/{{ workflow_id }}/status"
                hx-trigger="every 2s"
                hx-swap="outerHTML"
            >
                <!-- This div will be replaced with updated status -->
            </div>
        {% endif %}
        
        <!-- Results (only show when completed) -->
        {% if workflow_data.status == 'completed' and workflow_data.result %}
            <div class="divider"></div>
            
            <!-- Final Response -->
            <div class="mb-6">
                <h3 class="text-xl font-bold mb-3">
                    <i class="fas fa-comment-alt mr-2 text-accent"></i>
                    AI Response
                </h3>
                <div class="p-4 bg-base-200 rounded-lg whitespace-pre-line">
                    {{ workflow_data.result.final_response }}
                </div>
            </div>
            
            <!-- Agent Results -->
            {% if workflow_data.result.agent_results %}
            <div class="mb-6">
                <h3 class="text-xl font-bold mb-3">
                    <i class="fas fa-robot mr-2 text-secondary"></i>
                    Agent Results
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {% for agent_name, agent_result in workflow_data.result.agent_results.items() %}
                    <div class="card bg-base-200">
                        <div class="card-body">
                            <h4 class="card-title text-lg">
                                {% if agent_name == "WebSearchAgent" %}
                                    <i class="fas fa-globe text-success mr-2"></i>
                                {% elif agent_name == "FileSearchAgent" %}
                                    <i class="fas fa-file-search text-warning mr-2"></i>
                                {% elif agent_name == "InputInterpreterAgent" %}
                                    <i class="fas fa-brain text-primary mr-2"></i>
                                {% else %}
                                    <i class="fas fa-cog text-info mr-2"></i>
                                {% endif %}
                                {{ agent_name.replace('Agent', '') }}
                            </h4>
                            
                            {% if agent_result.error %}
                                <div class="alert alert-warning alert-sm">
                                    <i class="fas fa-exclamation-triangle"></i>
                                    <span>{{ agent_result.error }}</span>
                                </div>
                            {% else %}
                                <div class="badge badge-success gap-2">
                                    <i class="fas fa-check"></i>
                                    Completed
                                </div>
                                
                                {% if agent_name == "WebSearchAgent" %}
                                    <p class="text-sm mt-2">
                                        <strong>Sources:</strong> {{ agent_result.source_count }}
                                    </p>
                                {% elif agent_name == "FileSearchAgent" %}
                                    <p class="text-sm mt-2">
                                        <strong>Files:</strong> {{ agent_result.files_found }}
                                    </p>
                                {% elif agent_name == "InputInterpreterAgent" %}
                                    <p class="text-sm mt-2">
                                        <strong>Intent:</strong> {{ agent_result.primary_intent }}
                                    </p>
                                {% endif %}
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        {% endif %}
        
        <!-- Actions -->
        <div class="flex flex-wrap gap-2 justify-center">
            <a href="/api/agents/web/query" class="btn btn-primary">
                <i class="fas fa-plus mr-2"></i>
                New Query
            </a>
            <a href="/" class="btn btn-outline">
                <i class="fas fa-home mr-2"></i>
                Home
            </a>
        </div>
    </div>
</div>
```

### 2. Results Component (`app/templates/components/results.html`)

```html
{% if success %}
    <!-- Final Response -->
    <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
            <h2 class="card-title text-2xl mb-4">
                <i class="fas fa-check-circle mr-2 text-success"></i>
                AI Response
            </h2>
            
            <div class="mb-4">
                <div class="text-sm text-base-content/70 mb-2">Your Query:</div>
                <div class="p-3 bg-base-200 rounded-lg italic">
                    "{{ query }}"
                </div>
            </div>
            
            <div class="divider"></div>
            
            <div class="prose prose-lg max-w-none">
                <div class="whitespace-pre-line">{{ result.final_response }}</div>
            </div>
        </div>
    </div>

    <!-- Agent Results -->
    {% if result.agent_results %}
    <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
            <h3 class="card-title text-xl mb-4">
                <i class="fas fa-robot mr-2 text-primary"></i>
                Agent Results Summary
            </h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {% for agent_name, agent_result in result.agent_results.items() %}
                <div class="card bg-base-200 shadow">
                    <div class="card-body p-4">
                        <h4 class="font-bold flex items-center mb-2">
                            {% if agent_name == "WebSearchAgent" %}
                                <i class="fas fa-globe text-success mr-2"></i>
                            {% elif agent_name == "FileSearchAgent" %}
                                <i class="fas fa-file-search text-warning mr-2"></i>
                            {% elif agent_name == "InputInterpreterAgent" %}
                                <i class="fas fa-brain text-primary mr-2"></i>
                            {% else %}
                                <i class="fas fa-cog text-info mr-2"></i>
                            {% endif %}
                            {{ agent_name.replace('Agent', '') }}
                        </h4>
                        
                        {% if agent_result.error %}
                            <div class="badge badge-error gap-2">
                                <i class="fas fa-times"></i>
                                Error
                            </div>
                            <p class="text-xs mt-1 text-error">{{ agent_result.error }}</p>
                        {% else %}
                            <div class="badge badge-success gap-2">
                                <i class="fas fa-check"></i>
                                Success
                            </div>
                            
                            {% if agent_name == "WebSearchAgent" %}
                                <div class="text-sm mt-2">
                                    <div class="stat-value text-2xl">{{ agent_result.source_count }}</div>
                                    <div class="stat-title">Sources Found</div>
                                </div>
                            {% elif agent_name == "FileSearchAgent" %}
                                <div class="text-sm mt-2">
                                    <div class="stat-value text-2xl">{{ agent_result.files_found }}</div>
                                    <div class="stat-title">Files Analyzed</div>
                                </div>
                            {% elif agent_name == "InputInterpreterAgent" %}
                                <div class="text-sm mt-2">
                                    <div class="stat-title">Intent</div>
                                    <div class="stat-value text-sm">{{ agent_result.primary_intent }}</div>
                                    <div class="stat-desc">{{ (agent_result.confidence * 100) | round }}% confidence</div>
                                </div>
                            {% endif %}
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    {% endif %}

    <!-- Workflow Execution Details -->
    {% if result.execution_plan %}
    <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
            <h3 class="card-title text-lg mb-4">
                <i class="fas fa-project-diagram mr-2 text-info"></i>
                Execution Details
            </h3>
            
            <div class="stats stats-vertical lg:stats-horizontal shadow">
                <div class="stat">
                    <div class="stat-title">Strategy</div>
                    <div class="stat-value text-sm">{{ result.execution_plan.execution_strategy | title }}</div>
                </div>
                
                <div class="stat">
                    <div class="stat-title">Coordination</div>
                    <div class="stat-value text-sm">{{ result.execution_plan.coordination_strategy | title }}</div>
                </div>
                
                <div class="stat">
                    <div class="stat-title">Duration</div>
                    <div class="stat-value text-sm">{{ result.execution_plan.estimated_duration | title }}</div>
                </div>
            </div>
        </div>
    </div>
    {% endif %}

{% else %}
    <!-- Error Display -->
    <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
            <h2 class="card-title text-2xl text-error mb-4">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                Error Processing Query
            </h2>
            
            <div class="mb-4">
                <div class="text-sm text-base-content/70 mb-2">Your Query:</div>
                <div class="p-3 bg-base-200 rounded-lg italic">
                    "{{ query }}"
                </div>
            </div>
            
            <div class="alert alert-error">
                <i class="fas fa-bug"></i>
                <span>{{ error }}</span>
            </div>
        </div>
    </div>
{% endif %}

<!-- Action Buttons -->
<div class="flex flex-wrap gap-2 justify-center mt-6">
    <button 
        hx-get="/api/agents/web/query"
        hx-target="body"
        class="btn btn-primary"
    >
        <i class="fas fa-plus mr-2"></i>
        New Query
    </button>
    <a href="/" class="btn btn-outline">
        <i class="fas fa-home mr-2"></i>
        Back to Home
    </a>
</div>
```

### 3. HTMX Configuration and Enhancements

```javascript
// Enhanced HTMX configuration
document.addEventListener('DOMContentLoaded', function() {
    // Configure HTMX
    htmx.config.globalViewTransitions = true;
    htmx.config.defaultSwapStyle = 'innerHTML';
    
    // Auto-resize textareas
    document.addEventListener('input', function(e) {
        if (e.target.matches('textarea')) {
            e.target.style.height = 'auto';
            e.target.style.height = e.target.scrollHeight + 'px';
        }
    });
    
    // Loading states
    document.addEventListener('htmx:beforeRequest', function(e) {
        // Add loading state to button
        if (e.target.matches('button[type="submit"]')) {
            e.target.classList.add('loading');
        }
    });
    
    document.addEventListener('htmx:afterRequest', function(e) {
        // Remove loading state
        if (e.target.matches('button[type="submit"]')) {
            e.target.classList.remove('loading');
        }
    });
    
    // Error handling
    document.addEventListener('htmx:responseError', function(e) {
        // Show error toast
        const toast = document.createElement('div');
        toast.className = 'toast toast-top toast-end';
        toast.innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Request failed. Please try again.</span>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => toast.remove(), 5000);
    });
});

// Global helper function for example queries
window.setQuery = function(query) {
    const queryInput = document.getElementById('query');
    if (queryInput) {
        queryInput.value = query;
        queryInput.style.height = 'auto';
        queryInput.style.height = queryInput.scrollHeight + 'px';
    }
};
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

### Backend Best Practices
1. **Error Handling**: Always wrap agent calls in try-catch blocks
2. **Async Operations**: Use background tasks for long-running queries
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Caching**: Cache frequently used agent responses
5. **Monitoring**: Log agent performance and errors
6. **Security**: Validate inputs and sanitize outputs
7. **Testing**: Write tests for your agent integrations

### Frontend Best Practices
1. **HTMX Patterns**:
   - Use `hx-indicator` for loading states
   - Implement `hx-trigger="every Xs"` for polling
   - Use `hx-swap` strategically for smooth updates
   
2. **DaisyUI Components**:
   - Leverage semantic component classes
   - Use theme system for consistent styling
   - Implement responsive design with grid system
   
3. **Performance**:
   - Minimize DOM updates with targeted swapping
   - Use HTMX caching for repeated requests
   - Optimize component templates for reusability

### HTMX-Specific Features
- **Auto-polling**: Workflow status updates without JavaScript
- **Progressive Enhancement**: Works without JavaScript enabled
- **Smooth Transitions**: Built-in view transitions
- **Error Handling**: Automatic retry and error display
- **Loading States**: Visual feedback during requests

## 🔄 Key Advantages of HTMX + DaisyUI

### Over Traditional JavaScript Frameworks:
- **Simpler**: Less JavaScript code to maintain
- **Faster**: Server-side rendering with dynamic updates
- **More Accessible**: Better default accessibility
- **Smaller Bundle**: No large client-side framework

### Over Traditional Forms:
- **Dynamic**: Real-time updates without page refresh
- **Responsive**: Immediate feedback to user actions
- **Modern UX**: Smooth interactions and transitions
- **Progressive**: Degrades gracefully without JavaScript

This modern integration provides a beautiful, fast, and maintainable web interface for your AI agent system with minimal JavaScript complexity while maximizing user experience.