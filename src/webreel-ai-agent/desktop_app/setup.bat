@echo off
REM Setup script cho Desktop App
REM Cài đặt tất cả dependencies và chuẩn bị môi trường

echo ============================================================
echo AI Video Tutor - Desktop App Setup
echo ============================================================
echo.

cd /d "%~dp0"

REM Step 1: Check Python
echo [Step 1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Step 2: Check Node.js
echo [Step 2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js 18+ from: https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

REM Step 3: Create virtual environment
echo [Step 3/5] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)
echo.

REM Step 4: Install Python dependencies
echo [Step 4/5] Installing Python dependencies...
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install flet requests python-dotenv playwright edge-tts
echo [INFO] Skipping browser-use (has long path issues on Windows)
echo [INFO] Will use local browser-use copy instead
echo.

REM Step 5: Install Playwright browsers
echo [Step 5/5] Installing Playwright browsers...
.venv\Scripts\playwright install chromium
echo.

REM Step 6: Build Webreel CLI
echo [Step 6/6] Building Webreel CLI...
if exist "webreel\package.json" (
    cd webreel
    
    REM Check if dist exists
    if exist "dist\index.js" (
        echo [INFO] Webreel CLI already built
    ) else (
        echo [INFO] Building Webreel CLI...
        
        REM Fix package.json workspace protocol
        powershell -Command "(Get-Content package.json) -replace 'workspace:\*', 'file:../../packages/core' | Set-Content package.json.tmp"
        move /Y package.json.tmp package.json
        
        call npm install
        
        REM Use PowerShell for rm command
        powershell -Command "if (Test-Path dist) { Remove-Item -Recurse -Force dist }"
        call npm run build
        
        if exist "dist\index.js" (
            echo [SUCCESS] Webreel CLI built successfully
        ) else (
            echo [WARNING] Webreel build may have failed
            echo [INFO] You can manually build: cd webreel && npm run build
        )
    )
    cd ..
) else (
    echo [WARNING] webreel folder not found
    echo [INFO] Webreel CLI is required for video recording
)
echo.

REM Step 6: Setup .env
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from template...
        copy .env.example .env
        echo.
        echo [ACTION REQUIRED] Please edit .env and add your GEMINI_API_KEY
        echo Get API key from: https://aistudio.google.com/app/apikey
    )
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Edit .env and add your GEMINI_API_KEY
echo   2. Run: start-desktop.bat
echo.
pause
