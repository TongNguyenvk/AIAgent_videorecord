@echo off
REM Quick start script for local development (no Docker)

echo ========================================
echo Webreel AI Agent - Local Development
echo ========================================
echo.

REM Check if Chrome is running
echo [1/3] Checking Chrome...
curl -s http://localhost:9222/json/version >nul 2>&1
if %errorlevel% neq 0 (
    echo Chrome not running. Starting Chrome with debug port...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-debug"
    timeout /t 3 /nobreak >nul
    echo Chrome started on port 9222
) else (
    echo Chrome already running on port 9222
)
echo.

REM Check Python dependencies
echo [2/3] Checking Python dependencies...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
) else (
    echo Python dependencies OK
)
echo.

REM Start backend
echo [3/3] Starting FastAPI backend...
echo.
echo Backend will be available at: http://localhost:8000
echo Press Ctrl+C to stop
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
