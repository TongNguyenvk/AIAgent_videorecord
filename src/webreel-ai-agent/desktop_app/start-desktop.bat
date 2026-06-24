@echo off
REM Khởi động Desktop App (Standalone)
REM Không cần backend, chạy pipeline trực tiếp

echo ============================================================
echo AI Video Tutor - Desktop App (Standalone)
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if .env exists
if not exist ".env" (
    if exist ".env.example" (
        echo [WARNING] .env not found. Copying from .env.example...
        copy .env.example .env
        echo [INFO] Please edit .env and add your GEMINI_API_KEY
        pause
        exit /b 1
    ) else (
        echo [ERROR] .env.example not found!
        pause
        exit /b 1
    )
)

REM Check if venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: setup.bat
    pause
    exit /b 1
)

REM Check if flet is installed
.venv\Scripts\python.exe -c "import flet" 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencies not installed!
    echo Please run: setup.bat
    pause
    exit /b 1
)

echo [INFO] Starting Desktop App...
echo.

.venv\Scripts\python.exe app_flet.py

pause

