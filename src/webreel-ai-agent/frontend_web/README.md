# AI Video Tutor - Web Frontend

Simple HTML/CSS/JavaScript frontend for AI Video Tutor v3 pipeline.

## Features

- Real-time progress updates via WebSocket
- Phase 2.5 interactive TTS script review
- Video playback and history
- No framework dependencies, pure vanilla JS

## Usage

1. Start backend:
```bash
cd webreel-ai-agent
venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2. Open browser:
```
http://localhost:8000
```

The frontend is automatically served by FastAPI at the root path.

## Architecture

- `index.html` - Main HTML structure
- `style.css` - Styling with gradient theme
- `app.js` - WebSocket client and UI logic

## WebSocket Flow

1. User submits job -> POST /api/jobs
2. Frontend connects to WebSocket -> ws://localhost:8000/ws/{job_id}
3. Backend sends progress updates in real-time
4. Phase 2.5: Frontend shows review UI, user edits, submits -> POST /api/jobs/{job_id}/review
5. Backend resumes pipeline
6. Job completes -> Frontend shows video

## No More Flickering!

Unlike Streamlit which re-renders the entire page, this frontend:
- Only updates changed DOM elements
- Uses WebSocket for push updates (no polling)
- Smooth animations with CSS transitions
- No full page reloads
