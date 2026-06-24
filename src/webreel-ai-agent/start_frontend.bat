@echo off
REM Streamlit Frontend Startup Script
REM This script starts the Streamlit frontend using the virtual environment Python

echo Starting Streamlit Frontend...
echo.

REM Set environment variables
set STREAMLIT_SERVER_PORT=8501
set STREAMLIT_SERVER_ADDRESS=localhost
set BACKEND_URL=http://localhost:8000

REM Check if .env file exists and load it
if exist .env (
    echo Loading environment variables from .env
    for /f "usebackq tokens=*" %%a in (".env") do (
        set %%a
    )
)

REM Start Streamlit app
echo Running Streamlit on %STREAMLIT_SERVER_ADDRESS%:%STREAMLIT_SERVER_PORT%
echo Backend API: %BACKEND_URL%
echo.

.\venv\Scripts\python.exe -m streamlit run src\app.py --server.port %STREAMLIT_SERVER_PORT% --server.address %STREAMLIT_SERVER_ADDRESS%

pause
