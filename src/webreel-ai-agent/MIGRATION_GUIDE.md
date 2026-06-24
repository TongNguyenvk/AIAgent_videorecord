# FastAPI Backend Migration Guide

## Architecture Overview

The system has been migrated from a single-process Streamlit architecture to a FastAPI backend with asynchronous task processing and WebSocket support. This enables multiple concurrent video generation requests while maintaining real-time progress updates.

### New Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                         │
│                     (User Interface)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ HTTP Client  │  │ WS Client    │  │ UI Components│         │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘         │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
          │ POST /api/jobs   │ ws://backend/ws/{job_id}
          │                  │
┌─────────▼──────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ API Endpoints│  │ WebSocket    │  │ Job Queue    │        │
│  │              │  │ Server       │  │ (In-Memory)  │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                │
│                            │                                    │
│                   ┌────────▼────────┐                          │
│                   │ Background Tasks│                          │
│                   │ (Async Pool)    │                          │
│                   └────────┬────────┘                          │
└────────────────────────────┼───────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ Pipeline Phases │
                    │ 1. Scout        │
                    │ 2. Parser       │
                    │ 3. TTS          │
                    │ 4. Injector     │
                    │ 5. Execution    │
                    │ 6. Composer     │
                    └─────────────────┘
```

### Key Changes

1. **Separation of Concerns**: UI logic (Streamlit) is decoupled from processing logic (FastAPI background tasks)
2. **Asynchronous Processing**: All I/O-bound operations use Python async/await for efficient concurrency
3. **Real-time Updates**: WebSocket connections provide live progress updates during video generation
4. **Concurrent Requests**: Multiple users can submit video generation requests simultaneously
5. **In-Memory Job Queue**: Lightweight job management without external dependencies

## Running the System

### Prerequisites

Ensure you have completed the setup steps in the main README:
- Python 3.12+ installed
- Virtual environment created and activated
- Dependencies installed from requirements.txt
- Environment variables configured in .env file

### Starting the Backend

Run the FastAPI backend server:

```bash
.\start_backend.bat
```

The backend will start on `http://localhost:8000` by default.

**Environment Variables:**
- `BACKEND_HOST`: Server host (default: 0.0.0.0)
- `BACKEND_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)

### Starting the Frontend

In a separate terminal, run the Streamlit frontend:

```bash
.\start_frontend.bat
```

The frontend will start on `http://localhost:8501` by default.

**Environment Variables:**
- `STREAMLIT_SERVER_PORT`: Frontend port (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Frontend address (default: localhost)
- `BACKEND_URL`: Backend API URL (default: http://localhost:8000)

### Verifying the Setup

1. Open your browser to `http://localhost:8501`
2. Submit a video generation request through the UI
3. Observe real-time progress updates
4. Check the backend logs for processing details

## API Reference

### REST Endpoints

#### Submit Job

```http
POST /api/jobs
Content-Type: application/json

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

#### Get Job Status

```http
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
```

#### List Jobs

```http
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

#### Download Video

```http
GET /api/jobs/{job_id}/video

Response (200 OK):
Content-Type: video/mp4
Content-Disposition: attachment; filename="demo_final.mp4"

[Binary video data]
```

#### Health Check

```http
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

### WebSocket Protocol

Connect to the WebSocket endpoint to receive real-time progress updates:

```
ws://localhost:8000/ws/{job_id}
```

**Message Format:**

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

**Connection Lifecycle:**
1. Client connects with job_id
2. Server sends initial job status
3. Server broadcasts progress updates as job executes
4. Server sends final status message on completion
5. Connection closes gracefully

## Troubleshooting

### Backend fails to start

**Issue:** Port 8000 already in use

**Solution:** Change the port in start_backend.bat or stop the conflicting process

```bash
set BACKEND_PORT=8001
```

### Frontend cannot connect to backend

**Issue:** Connection refused or CORS errors

**Solution:** Verify backend is running and BACKEND_URL is correct

```bash
# Check backend health
curl http://localhost:8000/health

# Update frontend environment variable
set BACKEND_URL=http://localhost:8000
```

### WebSocket connection fails

**Issue:** WebSocket disconnects immediately or fails to connect

**Solution:** The system automatically falls back to HTTP polling. Check browser console for errors and verify the job_id is valid.

### Job stuck in "pending" status

**Issue:** Background task not starting

**Solution:** Check backend logs for errors. Restart the backend server.

```bash
# View backend logs
# Check terminal where start_backend.bat is running
```

### Video generation fails

**Issue:** Job status shows "failed" with error message

**Solution:** 
1. Check the error message in the job status response
2. Verify Chrome debug mode is running (for CDP mode)
3. Check that all dependencies are installed
4. Review backend logs for detailed stack traces

### Out of memory errors

**Issue:** System runs out of memory with multiple concurrent jobs

**Solution:** The in-memory job queue stores all job history. For production use, implement job cleanup or use a persistent database.

## Configuration

### Backend Configuration

Edit `backend/main.py` to customize:

- CORS origins (allow additional frontend URLs)
- Static file directory (change video output location)
- Job queue size limits
- Timeout settings

### Frontend Configuration

Edit `frontend/api_client.py` to customize:

- API request timeouts
- Retry logic
- Polling intervals for HTTP fallback

### Environment Variables

Create a `.env` file in the `webreel-ai-agent` directory:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
FPT_API_KEY=your_fpt_api_key_here

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
LOG_LEVEL=info

# Frontend Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
BACKEND_URL=http://localhost:8000
```

## Deployment Considerations

### Production Deployment

For production use, consider:

1. **Persistent Job Storage**: Replace in-memory job queue with Redis or database
2. **Process Manager**: Use systemd, supervisor, or PM2 to manage backend/frontend processes
3. **Reverse Proxy**: Use nginx or Apache to handle SSL and load balancing
4. **Monitoring**: Add application monitoring (Prometheus, Grafana)
5. **Logging**: Configure structured logging to files or log aggregation service
6. **Resource Limits**: Set memory and CPU limits for background tasks
7. **Job Cleanup**: Implement automatic cleanup of old jobs and video files

### Docker Deployment

The existing Docker setup can be extended to support the new architecture:

1. Create separate services for backend and frontend in docker-compose.yml
2. Use Docker networks for inter-service communication
3. Mount volumes for persistent job storage and video output
4. Configure health checks for both services

## Migration Checklist

If migrating from the old single-process architecture:

- [ ] Install new dependencies from backend/requirements.txt
- [ ] Update .env file with new configuration variables
- [ ] Test backend startup with start_backend.bat
- [ ] Test frontend startup with start_frontend.bat
- [ ] Verify WebSocket connections work
- [ ] Test concurrent job submissions
- [ ] Verify video history displays correctly
- [ ] Update any custom scripts or integrations to use new API
- [ ] Review and update monitoring/alerting configurations

## Additional Resources

- Backend API Documentation: See `backend/README.md`
- Frontend Integration Guide: See `frontend/README.md`
- Logging Configuration: See `backend/LOGGING.md`
- Task Implementation Details: See task summary files in `backend/` directory
