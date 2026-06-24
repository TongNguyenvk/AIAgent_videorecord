@echo off
echo ============================================================
echo Starting OS Worker
echo ============================================================
echo.
echo Configuration:
echo   Worker ID: os-worker-dev-1
echo   Queue: os-queue
echo   Idle Detection: DISABLED (IDLE_THRESHOLD=0)
echo   Upload: ENABLED
echo.
echo Press Ctrl+C to stop worker
echo ============================================================
echo.

python -m worker.os_worker

pause
