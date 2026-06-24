@echo off
REM Test script để kiểm tra venv và dependencies

cd /d "%~dp0"

echo ============================================================
echo Testing Desktop App Virtual Environment
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: setup.bat
    pause
    exit /b 1
)

echo [INFO] Virtual environment found
echo.

echo [Test] Python version:
.venv\Scripts\python.exe --version
echo.

echo [Test] Running test_all.py...
.venv\Scripts\python.exe test_all.py

pause
