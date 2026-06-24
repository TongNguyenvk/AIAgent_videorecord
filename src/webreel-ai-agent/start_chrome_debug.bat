@echo off
REM Script khởi động Chrome với Remote Debugging để browser-use có thể kết nối

echo ========================================
echo Starting Chrome with Remote Debugging
echo ========================================

REM Đóng tất cả Chrome đang chạy
echo Closing existing Chrome instances...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

REM Khởi động Chrome với remote debugging
echo Starting Chrome with debug port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" ^
  --profile-directory="Default"

echo.
echo ========================================
echo Chrome started successfully!
echo ========================================
echo.
echo Debug port: 9222
echo You can now run your automation script
echo.
echo To test connection, open: http://localhost:9222/json
echo.
echo Chrome is running in background. Do NOT close this window.
echo Press Ctrl+C to stop Chrome.
echo.

REM Keep window open and wait
timeout /t -1
