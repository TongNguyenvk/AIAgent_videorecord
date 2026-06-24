# Design Document: FastAPI Backend Migration

## Overview

This design document specifies the architecture for migrating the current Streamlit single-process video generation system to a FastAPI backend with asynchronous task processing and WebSocket support. The migration addresses the fundamental limitation of the current architecture where the entire 6-phase pipeline blocks the UI thread, preventing concurrent request handling.

The new architecture separates concerns into three layers:

1. **Presentation Layer**: Streamlit frontend for user interaction
2. **API Layer**: FastAPI backend with RESTful endpoints and WebSocket server
3. **Processing Layer**: Asynchronous background tasks executing the pipeline

This separation enables multiple concurrent video generation requests while maintaining real-time progress visibility through WebSocket connections. The design prioritizes simplicity by using in-memory data structures instead of external dependencies like Redis or message queues.

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Streamlit Frontend"
        UI[User Interface]
        WS_Client[WebSocket Client]
        HTTP_Client[HTTP Client]
    end
    
    subgraph "FastAPI Backend"
        API[API Endpoints]
        WS_Server[WebSocket Server]
        Job_Queue[In-Memory Job Queue]
        BG_Tasks[Background Task Pool]
        Static[Static File Server]
    end
    
    subgraph "Pipeline Execution"
        Phase1[Phase 1: Scout]
        Phase2[Phase 2: Parser]
        Phase3[Phase 3: TTS]
        Phase4[Phase 4: Injector]
        Phase5[Phase 5: Execution]
        Phase6[Phase 6: Composer]
    end
    
    UI -->|POST /api/jobs| API
    API -->|Create Job| Job_Queue
    API -->|Spawn| BG_Tasks
    UI -->|Connect| WS_Client
    WS_Client <-->|Progress Updates| WS_Server
    WS_Server -->|Read Status| Job_Queue
    BG_Tasks -->|Update Status| Job_Queue
    BG_Tasks --> Phase1
    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> Phase5
    Phase5 --> Phase6
    Phase6 -->|Write Output| Static
    HTTP_Client -->|GET /api/jobs/{id}/video| Static
```

### Architectural Principles

1. **Separation of Concerns**: UI logic (Streamlit) is completely decoupled from processing logic (FastAPI background tasks)
2. **Asynchronous Processing**: All I/O-bound operations use Python async/await for efficient concurrency
3. **Stateless API**: Each API request is independent; state is maintained only in the Job Queue
4. **Progressive Enhancement**: WebSocket provides real-time updates, but HTTP polling serves as fallback
5. **Minimal Dependencies**: In-memory job queue eliminates need for Redis or database

### Concurrency Model

The system uses Python's asyncio event loop for concurrency:

- **API Request Handling**: Each HTTP request runs in an async handler, allowing thousands of concurrent connections
- **Background Tasks**: FastAPI's BackgroundTasks spawns tasks that run independently of request lifecycle
- **Job Queue Access**: asyncio.Lock protects the in-memory dictionary from race conditions
- **WebSocket Connections**: Each WebSocket connection runs in its own coroutine, multiplexed on the event loop

## Components and Interfaces

### Component 1: FastAPI Backend Server

**Responsibility**: Serve HTTP API endpoints, manage WebSocket connections, coordinate background tasks

**Implementation**:
```python
from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio

app = FastAPI(title="Webreel Video Generation API")

# CORS configuration for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for video downloads
app.mount("/videos", StaticFiles(directory="output"), name="videos")

# Global job queue with asyncio lock
job_queue: dict[str, dict] = {}
job_queue_lock = asyncio.Lock()
```

**Configuration**:
- Host: 0.0.0.0 (bind to all interfaces)
- Port: 8000 (configurable via environment variable)
- Workers: 1 (single process, asyncio handles concurrency)
- Timeout: 300 seconds for long-running requests

### Component 2: In-Memory Job Queue

**Responsibility**: Store and manage job metadata, status, and results

**Data Structure**:
```python
job_queue = {
    "job_id_uuid": {
        "job_id": "job_id_uuid",
        "status": "pending" | "running" | "completed" | "failed" | "interrupted",
        "task": "Task description",
        "video_name": "output_video_name",
        "config": {
            "enable_tts": True,
            "tts_voice": "banmai",
            "tts_engine": "fpt",
            "cdp_url": "http://localhost:9222",
            "padding_ms": 300
        },
        "progress": {
            "current_phase": 1,
            "phase_name": "Scout",
            "message": "Running browser-use agent...",
            "logs": []
        },
        "result": {
            "video_path": "/videos/demo/demo_final.mp4",
            "video_url": "http://localhost:8000/videos/demo/demo_final.mp4",
            "duration_seconds": 120.5
        },
        "error": None,
        "created_at": "2024-01-15T10:30:00Z",
        "started_at": "2024-01-15T10:30:01Z",
        "completed_at": "2024-01-15T10:35:00Z"
    }
}
```

**Thread Safety**:
```python
async def update_job_status(job_id: str, updates: dict):
    """Thread-safe job status update."""
    async with job_queue_lock:
        if job_id in job_queue:
            job_queue[job_id].update(updates)
```

### Component 3: Background Task Executor

**Responsibility**: Execute the 6-phase pipeline asynchronously, update job status, send progress updates

**Implementation**:
```python
async def execute_pipeline_task(job_id: str, task: str, config: dict):
    """Background task that runs the pipeline."""
    try:
        await update_job_status(job_id, {
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        })
        
        # Create progress callback
        async def progress_callback(phase: int, message: str):
            await update_job_status(job_id, {
                "progress": {
                    "current_phase": phase,
                    "phase_name": PHASE_NAMES[phase],
                    "message": message
                }
            })
            await broadcast_progress(job_id)
        
        # Execute pipeline (from webreel-ai-agent/run_pipeline.py)
        video_path = await run_pipeline_v3(
            task=task,
            video_name=config["video_name"],
            cdp_url=config["cdp_url"],
            enable_tts=config["enable_tts"],
            tts_voice=config["tts_voice"],
            tts_engine=config["tts_engine"],
            padding_ms=config["padding_ms"],
            progress_callback=progress_callback
        )
        
        # Update with success
        await update_job_status(job_id, {
            "status": "completed",
            "result": {
                "video_path": str(video_path),
                "video_url": f"/videos/{config['video_name']}/{video_path.name}"
            },
            "completed_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        await update_job_status(job_id, {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })
```

**Integration with Existing Pipeline**:

The background task calls the existing `run_pipeline_v3` function from `webreel-ai-agent/run_pipeline.py` with minimal modifications:

1. Add optional `progress_callback` parameter to `run_pipeline_v3`
2. Call `await progress_callback(phase, message)` at the start of each phase
3. No changes to phase logic or execution flow
4. Use venv Python interpreter: `.\venv\Scripts\python.exe`

### Component 4: WebSocket Server

**Responsibility**: Maintain persistent connections for real-time progress updates

**Implementation**:
```python
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
    
    async def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
    
    async def broadcast(self, job_id: str, message: dict):
        if job_id in self.active_connections:
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass  # Connection closed

manager = ConnectionManager()

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        # Send initial status
        async with job_queue_lock:
            if job_id in job_queue:
                await websocket.send_json(job_queue[job_id])
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(job_id, websocket)
```

**Message Protocol**:
```json
{
  "type": "progress",
  "job_id": "uuid",
  "status": "running",
  "progress": {
    "current_phase": 3,
    "phase_name": "TTS",
    "message": "Generating audio segment 5/10",
    "logs": ["Generated audio for segment 1", "Generated audio for segment 2"]
  }
}
```

### Component 5: RESTful API Endpoints

**Endpoint 1: Submit Job**
```
POST /api/jobs
Content-Type: application/json

Request Body:
{
  "task": "Navigate to example.com and explain the homepage",
  "video_name": "demo",
  "config": {
    "enable_tts": true,
    "tts_voice": "banmai",
    "tts_engine": "fpt",
    "cdp_url": "http://localhost:9222",
    "padding_ms": 300
  }
}

Response (201 Created):
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "websocket_url": "ws://localhost:8000/ws/uuid"
}
```

**Endpoint 2: Get Job Status**
```
GET /api/jobs/{job_id}

Response (200 OK):
{
  "job_id": "uuid",
  "status": "running",
  "task": "Navigate to example.com",
  "progress": {
    "current_phase": 3,
    "phase_name": "TTS",
    "message": "Generating audio..."
  },
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:01Z"
}

Response (404 Not Found):
{
  "detail": "Job not found"
}
```

**Endpoint 3: List Jobs**
```
GET /api/jobs?status=completed&limit=10

Response (200 OK):
{
  "jobs": [
    {
      "job_id": "uuid1",
      "status": "completed",
      "task": "Task 1",
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 1
}
```

**Endpoint 4: Download Video**
```
GET /api/jobs/{job_id}/video

Response (200 OK):
Content-Type: video/mp4
Content-Disposition: attachment; filename="demo_final.mp4"

[Binary video data]

Response (404 Not Found):
{
  "detail": "Video not found or job not completed"
}
```

**Endpoint 5: Health Check**
```
GET /health

Response (200 OK):
{
  "status": "healthy",
  "version": "1.0.0",
  "jobs": {
    "pending": 2,
    "running": 3,
    "completed": 150,
    "failed": 5
  }
}
```

### Component 6: Streamlit Frontend Integration

**Responsibility**: Provide user interface, submit jobs, display progress, show results

**Implementation Changes**:

1. **Job Submission**:
```python
import requests
import streamlit as st

def submit_job(task: str, config: dict):
    response = requests.post(
        "http://localhost:8000/api/jobs",
        json={"task": task, "video_name": config["video_name"], "config": config}
    )
    return response.json()
```

2. **WebSocket Progress Tracking**:
```python
import websocket
import json
import threading

def track_progress(job_id: str, progress_container):
    ws = websocket.WebSocketApp(
        f"ws://localhost:8000/ws/{job_id}",
        on_message=lambda ws, msg: handle_progress(msg, progress_container),
        on_error=lambda ws, err: st.error(f"WebSocket error: {err}"),
        on_close=lambda ws: None
    )
    
    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

def handle_progress(message: str, progress_container):
    data = json.loads(message)
    progress_container.progress(
        data["progress"]["current_phase"] / 6,
        text=data["progress"]["message"]
    )
```

3. **HTTP Polling Fallback**:
```python
def poll_job_status(job_id: str):
    while True:
        response = requests.get(f"http://localhost:8000/api/jobs/{job_id}")
        job = response.json()
        
        if job["status"] in ["completed", "failed"]:
            return job
        
        time.sleep(2)
```

## Data Models

### Job Model

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4

class JobConfig(BaseModel):
    enable_tts: bool = True
    tts_voice: str = "banmai"
    tts_engine: Literal["fpt", "edge"] = "fpt"
    cdp_url: str = "http://localhost:9222"
    padding_ms: int = 300

class JobProgress(BaseModel):
    current_phase: int
    phase_name: str
    message: str
    logs: list[str] = []

class JobResult(BaseModel):
    video_path: str
    video_url: str
    duration_seconds: Optional[float] = None

class Job(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    status: Literal["pending", "running", "completed", "failed", "interrupted"]
    task: str
    video_name: str
    config: JobConfig
    progress: Optional[JobProgress] = None
    result: Optional[JobResult] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
```

### API Request/Response Models

```python
class JobSubmitRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=1000)
    video_name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    config: JobConfig = Field(default_factory=JobConfig)

class JobSubmitResponse(BaseModel