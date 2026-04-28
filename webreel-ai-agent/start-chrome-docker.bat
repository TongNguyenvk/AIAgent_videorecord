@echo off
REM Start Chrome with Docker-compatible CDP settings

echo Closing existing Chrome instances...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo Starting Chrome with remote debugging...
REM Đã thêm cờ --remote-debugging-address=0.0.0.0 để Docker có thể chọc vào
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --remote-allow-origins=* --user-data-dir="%TEMP%\chrome-debug"

echo Chrome started on port 9222 with Docker access enabled (0.0.0.0)
echo You can now run: docker-compose -f docker-compose.backend.yml restart
pause