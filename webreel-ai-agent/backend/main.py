"""
FastAPI Backend for Webreel Video Generation
Provides REST API endpoints and WebSocket support for asynchronous video generation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from backend.models import (
    JobSubmitRequest,
    JobSubmitResponse,
    Job,
    JobConfig,
    JobProgress,
    JobResult
)
from backend.tasks import execute_pipeline_task
from backend.websocket import manager
from backend.logging_config import setup_logging
from backend.middleware import RequestLoggingMiddleware
from backend.output_paths import build_video_url, resolve_output_dir
from backend.shutdown import ShutdownHandler
from backend.queue import JobQueue

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Global job queue with asyncio lock
job_queue: dict[str, dict] = {}
job_queue_lock = asyncio.Lock()

# Track running asyncio tasks for immediate cancellation
job_tasks: dict[str, asyncio.Task] = {}
job_tasks_lock = asyncio.Lock()

# Redis queue (production mode)
redis_queue = JobQueue()
_result_listener_task: Optional[asyncio.Task] = None

# Initialize shutdown handler
shutdown_handler = ShutdownHandler(
    job_queue=job_queue,
    job_queue_lock=job_queue_lock,
    connection_manager=manager
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan event handler.
    
    Handles startup and shutdown events for the FastAPI application.
    
    Requirements: 10.1, 10.5
    """
    global _result_listener_task
    
    # Startup
    shutdown_handler.register_signal_handlers()
    await shutdown_handler.load_job_queue()
    
    # Start Redis result listener (polls worker results in background)
    _result_listener_task = asyncio.create_task(_listen_for_worker_results())
    
    logger.info("FastAPI backend started successfully")
    if redis_queue.redis:
        logger.info(f"Redis queue connected: {redis_queue.redis_url}")
    else:
        logger.info("Redis not available, using direct execution mode only")
    
    yield
    
    # Shutdown
    if _result_listener_task:
        _result_listener_task.cancel()
    logger.info("FastAPI backend shutting down")


app = FastAPI(
    title="Webreel Video Generation API",
    description="Asynchronous video generation backend with real-time progress updates",
    version="1.0.0",
    lifespan=lifespan
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for video downloads
output_dir = resolve_output_dir()
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(output_dir)), name="videos")


async def _listen_for_worker_results():
    """Background task that polls Redis for worker results and updates job status.
    
    When a worker completes a job, it stores the result in Redis and publishes
    a notification. This listener picks up those results and updates the
    in-memory job queue + broadcasts via WebSocket.
    """
    import json as _json
    
    if not redis_queue.redis:
        logger.info("Redis not available, result listener disabled")
        return
    
    logger.info("Redis result listener started")
    
    try:
        pubsub = redis_queue.redis.pubsub()
        pubsub.subscribe("job-updates")
        
        while True:
            message = pubsub.get_message(timeout=2.0)
            if message and message["type"] == "message":
                try:
                    data = _json.loads(message["data"])
                    job_id = data.get("job_id")
                    if not job_id:
                        continue
                    
                    # Fetch full result from Redis
                    result = redis_queue.get_result(job_id)
                    if not result:
                        continue
                    
                    # Update in-memory job queue
                    async with job_queue_lock:
                        if job_id in job_queue:
                            job_queue[job_id]["status"] = result.get("status", "completed")
                            job_queue[job_id]["result"] = {
                                "video_path": result.get("video_path", ""),
                                "video_url": build_video_url(result["video_path"]) if result.get("video_path") else "",
                                "duration_seconds": None,
                            }
                            if result.get("error"):
                                job_queue[job_id]["error"] = result["error"]
                            job_queue[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                    
                    # Broadcast to WebSocket clients
                    await broadcast_progress(job_id)
                    logger.info(f"Worker result received for Job {job_id}: {result.get('status')}")
                    
                except Exception as e:
                    logger.warning(f"Error processing worker result: {e}")
            
            await asyncio.sleep(0.5)
    
    except asyncio.CancelledError:
        logger.info("Redis result listener stopped")
        pubsub.unsubscribe()
    except Exception as e:
        logger.error(f"Result listener error: {e}", exc_info=True)


async def update_job_status(job_id: str, updates: dict) -> None:
    """
    Thread-safe helper function to update job status in the queue.
    
    Args:
        job_id: Unique identifier for the job
        updates: Dictionary of fields to update in the job entry
    """
    async with job_queue_lock:
        if job_id in job_queue:
            job_queue[job_id].update(updates)


async def execute_pipeline_with_tracking(
    job_id: str,
    task: str,
    video_name: str,
    config: dict
):
    """
    Wrapper for execute_pipeline_task that tracks active task count.
    
    Increments active task counter before execution and decrements after completion.
    Handles task cancellation for immediate stop.
    
    Requirements: 10.2
    """
    try:
        # Increment active task counter
        await shutdown_handler.increment_active_tasks()
        
        # Setup pause event for Phase 2.5 review
        import asyncio
        pause_event = asyncio.Event()
        
        # Set pause event in pipeline module using job_id
        import sys
        from pathlib import Path
        agent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(agent_dir))
        from run_pipeline import set_review_pause_event
        set_review_pause_event(job_id, pause_event)
        
        # Execute the pipeline task
        await execute_pipeline_task(
            job_id=job_id,
            task=task,
            video_name=video_name,
            config=config,
            update_job_status_func=update_job_status,
            broadcast_progress_func=broadcast_progress
        )
    
    except asyncio.CancelledError:
        # Task was force cancelled by user
        logger.info(
            f"Job {job_id}: Task force cancelled (killed immediately)",
            extra={"job_id": job_id}
        )
        
        # Update job status if not already cancelled
        async with job_queue_lock:
            if job_id in job_queue and job_queue[job_id]["status"] != "cancelled":
                job_queue[job_id]["status"] = "cancelled"
                job_queue[job_id]["error"] = "Job force killed by user"
                job_queue[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Broadcast final state
        await broadcast_progress(job_id)
        
        # Re-raise to properly cancel the task
        raise
    
    finally:
        # Clean up pause event
        from run_pipeline import clear_review_pause_event
        clear_review_pause_event(job_id)
        
        # Remove task reference
        async with job_tasks_lock:
            if job_id in job_tasks:
                del job_tasks[job_id]
        
        # Always decrement counter, even if task fails
        await shutdown_handler.decrement_active_tasks()


async def broadcast_progress(job_id: str) -> None:
    """
    Broadcast current job status to all connected WebSocket clients.
    
    Args:
        job_id: Unique identifier for the job
    
    Requirements: 4.3, 4.4, 4.5
    """
    async with job_queue_lock:
        if job_id in job_queue:
            job_data = job_queue[job_id].copy()
        else:
            return
    
    # Broadcast to all connected clients for this job
    await manager.broadcast(job_id, job_data)


@app.post("/api/jobs", response_model=JobSubmitResponse, status_code=201)
async def submit_job(request: JobSubmitRequest, background_tasks: BackgroundTasks):
    """
    Submit a new video generation job.
    
    Creates a new job entry in the queue with pending status, spawns a background
    task to execute the pipeline, and returns the job_id and websocket_url for
    progress tracking.
    
    Requirements: 8.1, 2.3, 1.1, 3.1, 3.6, 10.1
    """
    # Check if server is accepting new jobs
    if not shutdown_handler.is_accepting_jobs():
        logger.warning("Job submission rejected: server is shutting down")
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: Server is shutting down"
        )
    
    # Generate unique job_id
    job_id = str(uuid4())
    
    logger.info(
        f"Job submitted: {job_id}",
        extra={
            "job_id": job_id,
            "task": request.task[:100],  # Truncate long tasks
            "video_name": request.video_name
        }
    )
    
    # Initialize job entry
    job_entry = {
        "job_id": job_id,
        "status": "pending",
        "task": request.task,
        "video_name": request.video_name,
        "config": request.config.model_dump(),
        "progress": None,
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None
    }
    
    # Add to job queue
    async with job_queue_lock:
        job_queue[job_id] = job_entry
    
    # Create asyncio task for immediate cancellation support
    task = asyncio.create_task(
        execute_pipeline_with_tracking(
            job_id=job_id,
            task=request.task,
            video_name=request.video_name,
            config=request.config.model_dump()
        )
    )
    
    # Store task reference for cancellation
    async with job_tasks_lock:
        job_tasks[job_id] = task
    
    # Return response with websocket URL
    return JobSubmitResponse(
        job_id=job_id,
        status="pending",
        created_at=datetime.now(timezone.utc),
        websocket_url=f"ws://localhost:8000/ws/{job_id}"
    )


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Retrieve job status and metadata.
    
    Returns the current status, progress, result, and error information
    for the specified job. Returns 404 if job does not exist.
    
    Requirements: 8.2, 8.5
    """
    async with job_queue_lock:
        if job_id not in job_queue:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_queue[job_id].copy()
    
    return job_data


@app.get("/api/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 100):
    """
    List all jobs with optional status filtering and pagination.
    
    Returns jobs sorted by created_at timestamp in descending order.
    Supports filtering by status and limiting the number of results.
    
    Requirements: 8.3
    """
    async with job_queue_lock:
        jobs = list(job_queue.values())
    
    # Filter by status if provided
    if status:
        jobs = [job for job in jobs if job["status"] == status]
    
    # Sort by created_at (newest first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply limit
    jobs = jobs[:limit]
    
    return {
        "jobs": jobs,
        "total": len(jobs)
    }


@app.post("/api/jobs/{job_id}/review")
async def submit_review(job_id: str, request: dict):
    """
    Submit reviewed TTS script and resume pipeline execution.
    
    Args:
        job_id: UUID of the job
        request: Dictionary containing:
            - tts_script: list of reviewed narration segments
    
    Returns:
        dict: Confirmation message
    """
    async with job_queue_lock:
        if job_id not in job_queue:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_queue[job_id]
        
        # Check if job is waiting for review
        if job_data.get("status") != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Job is not running (status: {job_data.get('status')})"
            )
    
    # Get reviewed script
    tts_script = request.get("tts_script", [])
    if not tts_script:
        raise HTTPException(status_code=400, detail="tts_script is required")
    
    logger.info(
        f"Job {job_id}: Received reviewed TTS script with {len(tts_script)} segments",
        extra={"job_id": job_id, "segment_count": len(tts_script)}
    )
    
    # Set reviewed script in pipeline module using job_id
    try:
        import sys
        from pathlib import Path
        agent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(agent_dir))
        from run_pipeline import set_reviewed_script, get_review_pause_event
        
        set_reviewed_script(job_id, tts_script)
        
        # Get and set the pause event to resume pipeline
        pause_event = get_review_pause_event(job_id)
        if pause_event:
            pause_event.set()
            logger.info(f"Job {job_id}: Pipeline resumed after review")
        else:
            raise HTTPException(
                status_code=400,
                detail="Job is not waiting for review (no pause event found)"
            )
        
        return {
            "job_id": job_id,
            "message": "Review submitted, pipeline resumed",
            "segment_count": len(tts_script)
        }
    
    except Exception as e:
        logger.error(f"Failed to resume pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume pipeline: {str(e)}")


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a running job immediately by killing the asyncio task.
    
    This will forcefully terminate the pipeline execution, even if it's in the
    middle of a phase. Useful for breaking out of infinite loops or stuck operations.
    
    Returns:
        dict: Updated job status
    """
    async with job_queue_lock:
        if job_id not in job_queue:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_queue[job_id]
        current_status = job_data["status"]
        
        # Only allow cancelling pending or running jobs
        if current_status not in ["pending", "running"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status: {current_status}"
            )
        
        # Update job status
        job_data["status"] = "cancelled"
        job_data["error"] = "Job cancelled by user (force killed)"
        job_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    logger.info(
        f"Job {job_id}: Force cancellation requested",
        extra={"job_id": job_id, "previous_status": current_status}
    )
    
    # Kill the asyncio task immediately
    async with job_tasks_lock:
        if job_id in job_tasks:
            task = job_tasks[job_id]
            if not task.done():
                task.cancel()
                logger.info(f"Job {job_id}: Asyncio task cancelled (force kill)")
            # Remove task reference
            del job_tasks[job_id]
        else:
            logger.warning(f"Job {job_id}: No task found to cancel")
    
    # Broadcast cancellation to WebSocket clients
    await broadcast_progress(job_id)
    
    # Also set stop flag as backup (in case task checks it)
    try:
        import sys
        from pathlib import Path
        agent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(agent_dir))
        from run_pipeline import set_stop_flag
        set_stop_flag(job_id, True)
    except Exception as e:
        logger.warning(f"Failed to set stop flag: {e}")
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job force killed immediately"
    }


@app.get("/api/jobs/{job_id}/video")
async def download_video(job_id: str):
    """
    Download the generated video file.
    
    Returns the video file with appropriate Content-Disposition header
    for download. Returns 404 if job is not completed or video file is missing.
    
    Requirements: 8.4, 8.5
    """
    async with job_queue_lock:
        if job_id not in job_queue:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_queue[job_id]
    
    # Check if job is completed
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=404,
            detail=f"Video not available. Job status: {job_data['status']}"
        )
    
    # Check if result exists
    if not job_data.get("result") or not job_data["result"].get("video_path"):
        raise HTTPException(status_code=404, detail="Video file path not found")
    
    # Get video file path
    video_path = Path(job_data["result"]["video_path"])
    
    # Check if file exists
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    # Return file with download header
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=video_path.name,
        headers={"Content-Disposition": f'attachment; filename="{video_path.name}"'}
    )


@app.post("/api/upload-pptx")
async def upload_pptx(
    file: UploadFile,
    task: str = "Create a lecture video explaining each slide",
    tts_voice: str = "vi-VN-HoaiMyNeural",
    tts_engine: str = "edge",
    padding_ms: int = 500,
    language: str = "Vietnamese",
):
    """Upload a PPTX/PDF file and start the Slide-to-Video pipeline.
    
    Flow:
      1. Receives .pptx or .pdf file
      2. Saves to output directory
      3. Submits job to office-queue (Slide pipeline)
      4. Returns job_id + websocket URL for tracking
    """
    if not file.filename or not file.filename.lower().endswith((".pptx", ".ppt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .pptx, .ppt, or .pdf files are accepted")
    
    # Read file content
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 100MB.")
    
    # Generate job ID and video name
    job_id = str(uuid4())
    video_name = f"slide_{Path(file.filename).stem}_{job_id[:8]}"
    
    # Save file to output directory
    import os
    output_dir = resolve_output_dir()
    upload_dir = output_dir / video_name / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"PPTX uploaded: {file.filename} ({len(content)} bytes) -> {file_path}")
    
    # Submit to office-queue
    job_data = {
        "job_id": job_id,
        "video_name": video_name,
        "config": {
            "pptx_path": str(file_path),
            "task": task,
            "tts_voice": tts_voice,
            "tts_engine": tts_engine,
            "padding_ms": padding_ms,
            "language": language,
        },
    }
    
    redis_queue.push("office-queue", job_data)
    logger.info(f"Submitted to office-queue: {job_id}")
    
    return {
        "job_id": job_id,
        "video_name": video_name,
        "status": "queued",
        "file_name": file.filename,
        "file_size": len(content),
        "ws_url": f"/ws/{job_id}",
        "result_url": f"/api/queue/result/{job_id}",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with job statistics, queue stats, and shutdown status.
    """
    async with job_queue_lock:
        job_stats = {
            "pending": sum(1 for job in job_queue.values() if job["status"] == "pending"),
            "running": sum(1 for job in job_queue.values() if job["status"] == "running"),
            "completed": sum(1 for job in job_queue.values() if job["status"] == "completed"),
            "failed": sum(1 for job in job_queue.values() if job["status"] == "failed"),
        }
    
    # Redis queue stats
    queue_stats = redis_queue.get_all_queue_stats() if redis_queue.redis else {}
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "jobs": job_stats,
        "queues": queue_stats,
        "redis_connected": redis_queue.redis is not None,
        "is_shutting_down": shutdown_handler.is_shutting_down,
        "active_tasks": shutdown_handler.active_task_count
    }


@app.post("/api/admin/reset-shutdown")
async def reset_shutdown_flag():
    """
    Reset the shutdown flag (for debugging/recovery after uvicorn reload).
    
    This endpoint allows manually resetting the is_shutting_down flag
    in case it gets stuck after a uvicorn reload or false signal.
    """
    old_value = shutdown_handler.is_shutting_down
    shutdown_handler.is_shutting_down = False
    
    logger.warning(
        f"Shutdown flag manually reset from {old_value} to False",
        extra={"old_value": old_value, "new_value": False}
    )
    
    return {
        "message": "Shutdown flag reset successfully",
        "old_value": old_value,
        "new_value": False
    }


# =========================================================================
# Queue-based endpoints (production mode with Redis workers)
# =========================================================================

class QueueJobRequest(BaseModel):
    """Request model for queue-based job submission."""
    task: str
    video_name: str = ""
    job_type: str = "web"  # "web", "office", "os"
    config: dict = {}


@app.post("/api/queue/submit")
async def submit_queue_job(request: QueueJobRequest):
    """Submit a job to Redis queue for worker processing.
    
    Routes to the correct queue based on job_type:
      - web -> web-queue (Linux Docker worker)
      - office -> office-queue (Linux Docker worker)
      - os -> os-queue (Windows worker)
    """
    if not redis_queue.redis:
        raise HTTPException(status_code=503, detail="Redis not available. Use /api/jobs for direct execution.")
    
    queue_map = {
        "web": "web-queue",
        "office": "office-queue",
        "os": "os-queue",
    }
    queue_name = queue_map.get(request.job_type)
    if not queue_name:
        raise HTTPException(status_code=400, detail=f"Invalid job_type: {request.job_type}. Must be web, office, or os.")
    
    import time as _time
    job_id = str(uuid4())
    video_name = request.video_name or f"video_{int(_time.time())}"
    
    # Push to Redis queue
    redis_queue.push(queue_name, {
        "job_id": job_id,
        "task": request.task,
        "video_name": video_name,
        "config": request.config,
        "job_type": request.job_type,
    })
    
    # Also track in memory for status queries
    job_entry = {
        "job_id": job_id,
        "status": "queued",
        "task": request.task,
        "video_name": video_name,
        "config": request.config,
        "job_type": request.job_type,
        "queue": queue_name,
        "progress": None,
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
    }
    async with job_queue_lock:
        job_queue[job_id] = job_entry
    
    logger.info(f"Queue job submitted: {job_id} -> {queue_name}")
    
    return {
        "job_id": job_id,
        "queue": queue_name,
        "status": "queued",
        "websocket_url": f"ws://localhost:8000/ws/{job_id}",
    }


@app.get("/api/queue/stats")
async def get_queue_stats():
    """Get current queue lengths and worker status."""
    if not redis_queue.redis:
        return {"error": "Redis not connected", "queues": {}}
    
    return {
        "queues": redis_queue.get_all_queue_stats(),
        "redis_connected": True,
    }


@app.get("/api/queue/result/{job_id}")
async def get_queue_result(job_id: str):
    """Get result of a queue-processed job directly from Redis."""
    # Check in-memory first
    async with job_queue_lock:
        if job_id in job_queue:
            return job_queue[job_id]
    
    # Check Redis
    if redis_queue.redis:
        result = redis_queue.get_result(job_id)
        status = redis_queue.get_status(job_id)
        if result or status:
            return {
                "job_id": job_id,
                "status": status or "unknown",
                "result": result,
            }
    
    raise HTTPException(status_code=404, detail="Job not found")


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    
    Accepts WebSocket connections for a specific job_id, sends initial job status,
    and keeps the connection alive to receive progress updates. Handles disconnections
    gracefully.
    
    Requirements: 4.1, 4.2, 4.5, 4.6, 9.3
    """
    # Connect the WebSocket
    await manager.connect(job_id, websocket)
    
    try:
        # Send initial job status
        async with job_queue_lock:
            if job_id in job_queue:
                initial_status = job_queue[job_id].copy()
                await websocket.send_json(initial_status)
                logger.info(f"WebSocket connection established for job {job_id}")
            else:
                # Job not found, send error and close
                logger.warning(f"WebSocket connection attempted for non-existent job {job_id}")
                await websocket.send_json({
                    "error": "Job not found",
                    "job_id": job_id
                })
                await manager.disconnect(job_id, websocket)
                return
        
        # Keep connection alive and handle ping/pong
        while True:
            # Wait for messages from client (ping/pong or close)
            data = await websocket.receive_text()
            
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        # Client disconnected, clean up
        logger.info(f"WebSocket client disconnected for job {job_id}")
        await manager.disconnect(job_id, websocket)
    
    except Exception as e:
        # Handle other errors gracefully
        logger.error(
            f"WebSocket error for job {job_id}: {e}",
            extra={"job_id": job_id},
            exc_info=True
        )
        await manager.disconnect(job_id, websocket)


# Mount frontend static files LAST (after all API routes)
# This ensures API routes take precedence over static file serving
frontend_dir = Path(__file__).parent.parent / "frontend_web"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=300,
        reload=True
    )
