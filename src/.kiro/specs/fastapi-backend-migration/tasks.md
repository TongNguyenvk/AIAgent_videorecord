# Implementation Plan: FastAPI Backend Migration

## Overview

This implementation plan migrates the current Streamlit single-process architecture to a FastAPI backend with asynchronous task processing and WebSocket support. The migration separates the UI layer (Streamlit) from the processing layer (FastAPI), enabling multiple concurrent video generation requests while maintaining real-time progress updates.

The implementation follows an incremental approach: first establishing the FastAPI foundation, then adding job management, background processing, WebSocket support, and finally integrating the Streamlit frontend.

## Tasks

- [x] 1. Set up FastAPI backend foundation
  - [x] 1.1 Create FastAPI application with basic configuration
    - Create `webreel-ai-agent/backend/main.py` with FastAPI app instance
    - Configure CORS middleware for Streamlit frontend (port 8501)
    - Add static file serving for output directory
    - Configure uvicorn server settings (host, port, timeout)
    - _Requirements: 1.1, 1.3, 1.4_

  - [x] 1.2 Define Pydantic data models for API
    - Create `webreel-ai-agent/backend/models.py` with JobConfig, JobProgress, JobResult, Job models
    - Define JobSubmitRequest and JobSubmitResponse models
    - Add validation rules for task description and video_name fields
    - _Requirements: 1.1, 8.6_

  - [x] 1.3 Initialize in-memory job queue with thread safety
    - Create global job_queue dictionary in main.py
    - Add asyncio.Lock for concurrent access protection
    - Implement update_job_status() helper function with lock acquisition
    - _Requirements: 1.5, 2.1, 2.5_

- [x] 2. Implement job management API endpoints
  - [x] 2.1 Create POST /api/jobs endpoint for job submission
    - Implement job submission handler with request validation
    - Generate unique job_id using UUID
    - Initialize job entry in job_queue with "pending" status
    - Return job_id and websocket_url in response
    - _Requirements: 8.1, 2.3, 1.1_

  - [x] 2.2 Create GET /api/jobs/{job_id} endpoint for status queries
    - Implement job status retrieval with job_queue lookup
    - Return 404 error for non-existent jobs
    - Include progress, result, and error fields in response
    - _Requirements: 8.2, 8.5_

  - [x] 2.3 Create GET /api/jobs endpoint for listing jobs
    - Implement job listing with optional status filtering
    - Add pagination support with limit parameter
    - Return jobs sorted by created_at timestamp
    - _Requirements: 8.3_

  - [x] 2.4 Create GET /api/jobs/{job_id}/video endpoint for video downloads
    - Implement video file retrieval from output directory
    - Set Content-Disposition header for file downloads
    - Return 404 if job not completed or video file missing
    - _Requirements: 8.4, 8.5_

  - [x] 2.5 Create GET /health endpoint for health checks
    - Implement health check with job statistics
    - Count jobs by status (pending, running, completed, failed)
    - Return API version and status
    - _Requirements: 1.1_

- [x] 3. Implement background task processing
  - [x] 3.1 Modify run_pipeline_v3 to support progress callbacks
    - Add optional progress_callback parameter to run_pipeline_v3() in webreel-ai-agent/run_pipeline.py
    - Call await progress_callback(phase, message) at the start of each phase
    - Ensure backward compatibility for existing callers
    - Use venv Python: .\venv\Scripts\python.exe
    - _Requirements: 3.3, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 3.2 Create background task executor function
    - Create `webreel-ai-agent/backend/tasks.py` with execute_pipeline_task()
    - Import run_pipeline_v3 from webreel-ai-agent/run_pipeline.py
    - Update job status to "running" when task starts
    - Call run_pipeline_v3 with progress callback
    - Update job status to "completed" with result on success
    - Update job status to "failed" with error message on exception
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 9.1_

  - [x] 3.3 Integrate background tasks with job submission endpoint
    - Spawn background task using FastAPI BackgroundTasks
    - Pass job_id, task description, and config to background task
    - Return immediately after spawning task (non-blocking)
    - _Requirements: 3.1, 3.6_

- [x] 4. Implement WebSocket server for real-time updates
  - [x] 4.1 Create WebSocket connection manager
    - Create `webreel-ai-agent/backend/websocket.py` with ConnectionManager class
    - Implement connect() method to accept and store WebSocket connections
    - Implement disconnect() method to remove closed connections
    - Implement broadcast() method to send messages to all connections for a job_id
    - _Requirements: 4.1, 4.2_

  - [x] 4.2 Create WebSocket endpoint for progress updates
    - Implement /ws/{job_id} WebSocket endpoint
    - Send initial job status on connection
    - Keep connection alive with ping/pong
    - Handle WebSocketDisconnect gracefully
    - _Requirements: 4.1, 4.2, 4.5, 4.6_

  - [x] 4.3 Integrate WebSocket broadcasting with background tasks
    - Call ConnectionManager.broadcast() in progress callback
    - Send progress updates with phase number, phase name, and message
    - Send final status message on job completion or failure
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 5. Checkpoint - Ensure backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Refactor Streamlit frontend for API integration
  - [x] 6.1 Create API client module for backend communication
    - Create `webreel-ai-agent/frontend/api_client.py` with submit_job(), get_job_status(), list_jobs() functions
    - Use requests library for HTTP calls
    - Handle connection errors and timeouts gracefully
    - _Requirements: 5.1, 5.6_

  - [x] 6.2 Implement WebSocket client for progress tracking
    - Add WebSocket connection logic using websocket-client library
    - Implement track_progress() function with message handler
    - Update Streamlit UI components with progress data
    - Implement HTTP polling fallback if WebSocket fails
    - _Requirements: 5.3, 5.4, 5.5_

  - [x] 6.3 Refactor app.py to use API client instead of direct pipeline execution
    - Replace direct run_pipeline_v3() calls from run_pipeline.py with submit_job() API calls
    - Remove pipeline execution logic from Streamlit frontend
    - Update UI to display job_id and status
    - _Requirements: 5.1, 5.2_

  - [x] 6.4 Update video history to fetch from backend API
    - Replace local file system scanning with GET /api/jobs API call
    - Filter jobs by "completed" status
    - Display video metadata from API response
    - _Requirements: 7.4, 7.5_

  - [x] 6.5 Preserve existing UI features and configuration options
    - Ensure TTS provider selection (Edge TTS, FPT TTS) works with API
    - Ensure browser mode selection (CDP, Headless) works with API
    - Ensure all pipeline configuration parameters are passed to API
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 7. Implement error handling and logging
  - [x] 7.1 Add structured logging to FastAPI backend
    - Configure Python logging with JSON formatter
    - Log all API requests with method, path, status code, and duration
    - Add log level configuration via environment variable
    - _Requirements: 9.2, 9.4_

  - [x] 7.2 Add error logging to background tasks
    - Log phase failures with phase name, timestamp, and stack trace
    - Log job status transitions (pending → running → completed/failed)
    - Store error messages in job_queue for API retrieval
    - _Requirements: 9.1, 9.5_

  - [x] 7.3 Add error handling to WebSocket server
    - Catch and log WebSocket connection errors
    - Continue serving other connections on individual connection failure
    - Log connection/disconnection events
    - _Requirements: 9.3_

- [x] 8. Implement graceful shutdown handling
  - [x] 8.1 Add shutdown signal handlers
    - Register SIGTERM and SIGINT handlers
    - Set shutdown flag to stop accepting new jobs
    - Return 503 Service Unavailable for new job submissions during shutdown
    - _Requirements: 10.1_

  - [x] 8.2 Implement background task completion waiting
    - Wait up to 30 seconds for running background tasks to complete
    - Track active background tasks with counter
    - Force shutdown after timeout
    - _Requirements: 10.2_

  - [x] 8.3 Update interrupted jobs and close WebSocket connections
    - Update status to "interrupted" for jobs still running after timeout
    - Close all WebSocket connections with 1001 status code
    - Log shutdown completion
    - _Requirements: 10.3, 10.4_

  - [x] 8.4 Persist job queue state to disk
    - Serialize job_queue to JSON file on shutdown
    - Load job_queue from JSON file on startup if exists
    - Handle serialization errors gracefully
    - _Requirements: 10.5_

- [x] 9. Create deployment configuration and documentation
  - [x] 9.1 Create requirements.txt for backend dependencies
    - Add fastapi, uvicorn, websockets, python-multipart, pydantic
    - Pin versions for reproducibility
    - _Requirements: 1.1_

  - [x] 9.2 Create startup scripts for backend and frontend
    - Create `start_backend.bat` to run uvicorn server using .\venv\Scripts\python.exe
    - Create `start_frontend.bat` to run Streamlit app using .\venv\Scripts\python.exe
    - Add environment variable configuration
    - _Requirements: 1.1_

  - [x] 9.3 Update README with migration instructions
    - Document new architecture with diagram
    - Add instructions for running backend and frontend separately
    - Document API endpoints and WebSocket protocol
    - Add troubleshooting section
    - _Requirements: 1.1_

- [x] 10. Final checkpoint - End-to-end testing
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- The migration maintains backward compatibility by keeping the existing pipeline logic unchanged
- Background tasks run independently of HTTP request lifecycle, enabling true concurrency
- WebSocket provides real-time updates, with HTTP polling as fallback for reliability
- In-memory job queue eliminates external dependencies while supporting concurrent access
- Graceful shutdown ensures in-progress jobs complete or are safely marked as interrupted
