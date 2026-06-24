@echo off
REM FastAPI Backend Startup Script
REM This script starts the FastAPI backend server using the virtual environment Python

echo Starting FastAPI Backend Server...
echo.

REM Set environment variables
set BACKEND_HOST=0.0.0.0
set BACKEND_PORT=8000
set LOG_LEVEL=info

REM Check if .env file exists and load it
if exist .env (
    echo Loading environment variables from .env
    for /f "usebackq tokens=*" %%a in (".env") do (
        set %%a
    )
)

REM Start uvicorn server
echo Running uvicorn on %BACKEND_HOST%:%BACKEND_PORT%
echo Log level: %LOG_LEVEL%
echo.

.\venv\Scripts\python.exe -m uvicorn backend.main:app --host %BACKEND_HOST% --port %BACKEND_PORT% --log-level %LOG_LEVEL% --reload

pause
