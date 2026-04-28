# Requirements Document

## Introduction

This document specifies requirements for migrating the current Streamlit single-process architecture to a FastAPI backend with background task processing and WebSocket support. The current architecture runs the entire 6-phase video generation pipeline in a single thread, blocking the UI and preventing concurrent request handling. The new architecture will separate the UI layer (Streamlit) from the processing layer (FastAPI), enabling multiple concurrent video generation requests while maintaining real-time progress updates through WebSocket connections.

## Glossary

- **FastAPI_Backend**: The asynchronous HTTP server that handles API requests, manages background tasks, and serves WebSocket connections
- **Job_Queue**: An in-memory dictionary-based queue that stores job metadata and status information
- **Background_Task**: An asynchronous worker that executes the 6-phase pipeline independently of HTTP request handling
- **WebSocket_Server**: The component within FastAPI_Backend that maintains persistent connections for real-time progress updates
- **Streamlit_Frontend**: The user interface application that makes API calls to FastAPI_Backend but does not execute pipeline logic
- **Pipeline**: The 6-phase video generation process consisting of Scout, Parser, TTS, Injector, Execution, and Composer phases
- **Job**: A single video generation request with unique identifier, configuration, and status tracking
- **Progress_Update**: A message sent via WebSocket containing phase number, status message, and log entries
- **Video_History**: A persistent record of completed video generation jobs with metadata and file paths

## Requirements

### Requirement 1: FastAPI Backend Server

**User Story:** As a developer, I want a FastAPI backend server with async support, so that the system can handle multiple concurrent requests without blocking.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL expose HTTP endpoints for job submission, status queries, and result retrieval
2. THE FastAPI_Backend SHALL support asynchronous request handling using Python async/await
3. THE FastAPI_Backend SHALL serve static video files from the output directory
4. THE FastAPI_Backend SHALL provide CORS configuration to allow Streamlit_Frontend connections
5. WHEN FastAPI_Backend starts, THE FastAPI_Backend SHALL initialize the Job_Queue as an empty dictionary

### Requirement 2: In-Memory Job Queue

**User Story:** As a system administrator, I want a lightweight in-memory job queue, so that I can avoid external dependencies like Redis while supporting concurrent requests.

#### Acceptance Criteria

1. THE Job_Queue SHALL store job metadata using job_id as the dictionary key
2. FOR EACH Job, THE Job_Queue SHALL maintain status, configuration, progress, logs, and result file path
3. WHEN a Job is submitted, THE Job_Queue SHALL assign a unique job_id using UUID generation
4. WHEN a Job completes, THE Job_Queue SHALL retain the job metadata for history retrieval
5. THE Job_Queue SHALL support concurrent read and write operations using asyncio locks

### Requirement 3: Background Task Processing

**User Story:** As a user, I want video generation to run in the background, so that I can submit multiple requests and continue using the UI without blocking.

#### Acceptance Criteria

1. WHEN a video generation request is received, THE FastAPI_Backend SHALL create a Background_Task to execute the Pipeline
2. THE Background_Task SHALL execute all 6 phases of the Pipeline asynchronously
3. WHILE a Background_Task is running, THE Background_Task SHALL update job status in the Job_Queue after each phase
4. IF a Background_Task encounters an error, THEN THE Background_Task SHALL update job status to "failed" and log the error message
5. WHEN a Background_Task completes successfully, THE Background_Task SHALL update job status to "completed" and store the output file path
6. THE FastAPI_Backend SHALL support multiple concurrent Background_Tasks executing different Jobs

### Requirement 4: WebSocket Real-Time Progress Updates

**User Story:** As a user, I want to see real-time progress updates while my video is being generated, so that I know the current status and can monitor the process.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL accept client connections at a dedicated WebSocket endpoint
2. WHEN a client connects, THE WebSocket_Server SHALL require a job_id parameter for connection authentication
3. WHILE a Background_Task is executing, THE Background_Task SHALL send Progress_Updates through the WebSocket_Server
4. THE Progress_Update SHALL include phase number, phase name, status message, and log entries
5. WHEN a Job completes or fails, THE WebSocket_Server SHALL send a final status message and close the connection gracefully
6. IF a WebSocket connection is lost, THEN THE Background_Task SHALL continue execution without interruption

### Requirement 5: Streamlit Frontend API Integration

**User Story:** As a user, I want the Streamlit UI to remain familiar and functional, so that I can continue using the application without learning a new interface.

#### Acceptance Criteria

1. THE Streamlit_Frontend SHALL submit video generation requests to FastAPI_Backend via HTTP POST
2. THE Streamlit_Frontend SHALL NOT execute any Pipeline phases directly
3. WHEN a Job is submitted, THE Streamlit_Frontend SHALL establish a WebSocket connection to receive Progress_Updates
4. THE Streamlit_Frontend SHALL display real-time progress using the existing PipelineProgress UI component
5. THE Streamlit_Frontend SHALL poll job status via HTTP GET if WebSocket connection fails
6. WHEN a Job completes, THE Streamlit_Frontend SHALL retrieve the video file URL from FastAPI_Backend

### Requirement 6: Pipeline Phase Execution

**User Story:** As a system, I want to execute the existing 6-phase pipeline in background tasks, so that video generation logic remains unchanged while gaining concurrency support.

#### Acceptance Criteria

1. THE Background_Task SHALL execute phase1_scout to generate browser-use history
2. WHEN phase1_scout completes, THE Background_Task SHALL execute phase2_parser to convert history to webreel format
3. WHERE TTS is enabled, THE Background_Task SHALL execute phase3_tts to generate audio narration
4. WHERE TTS audio exists, THE Background_Task SHALL execute phase4_injector to add audio timing markers
5. THE Background_Task SHALL execute phase5_execution to record the video using webreel
6. THE Background_Task SHALL execute phase6_composer to finalize the video output
7. WHEN any phase fails, THE Background_Task SHALL halt execution and report the error

### Requirement 7: Configuration and Feature Preservation

**User Story:** As a user, I want all existing features to work after migration, so that I don't lose functionality like TTS options and browser modes.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL accept TTS provider configuration (Edge TTS or FPT TTS)
2. THE FastAPI_Backend SHALL accept browser mode configuration (CDP or Headless)
3. THE FastAPI_Backend SHALL accept all existing pipeline configuration parameters
4. THE Video_History SHALL persist completed jobs with metadata including task description, timestamp, and file path
5. THE Streamlit_Frontend SHALL display Video_History with playback and download options

### Requirement 8: Job Management API

**User Story:** As a developer, I want RESTful API endpoints for job management, so that I can submit jobs, query status, and retrieve results programmatically.

#### Acceptance Criteria

1. THE FastAPI_Backend SHALL provide POST /api/jobs endpoint to submit new video generation requests
2. THE FastAPI_Backend SHALL provide GET /api/jobs/{job_id} endpoint to retrieve job status and metadata
3. THE FastAPI_Backend SHALL provide GET /api/jobs endpoint to list all jobs with optional status filtering
4. THE FastAPI_Backend SHALL provide GET /api/jobs/{job_id}/video endpoint to download the generated video file
5. WHEN a Job does not exist, THE FastAPI_Backend SHALL return HTTP 404 with error message
6. THE FastAPI_Backend SHALL return job responses in JSON format with consistent schema

### Requirement 9: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging, so that I can diagnose issues and monitor system health.

#### Acceptance Criteria

1. WHEN a Pipeline phase fails, THE Background_Task SHALL log the error with phase name, timestamp, and stack trace
2. THE FastAPI_Backend SHALL log all API requests with method, path, and response status
3. IF a WebSocket connection error occurs, THEN THE WebSocket_Server SHALL log the error and continue serving other connections
4. THE FastAPI_Backend SHALL provide structured logging with configurable log levels
5. WHEN a Job fails, THE Job_Queue SHALL store the error message for retrieval via API

### Requirement 10: Graceful Shutdown and Cleanup

**User Story:** As a system administrator, I want graceful shutdown handling, so that in-progress jobs can complete or be safely terminated.

#### Acceptance Criteria

1. WHEN FastAPI_Backend receives a shutdown signal, THE FastAPI_Backend SHALL stop accepting new job submissions
2. WHILE Background_Tasks are running, THE FastAPI_Backend SHALL wait up to 30 seconds for completion before forcing shutdown
3. WHEN shutdown timeout is reached, THE FastAPI_Backend SHALL update remaining jobs to "interrupted" status
4. THE FastAPI_Backend SHALL close all WebSocket connections with appropriate status codes during shutdown
5. THE FastAPI_Backend SHALL persist Job_Queue state to disk before shutdown for recovery
