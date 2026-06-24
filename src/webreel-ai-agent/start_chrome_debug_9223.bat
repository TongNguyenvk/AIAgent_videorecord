@echo off
echo Starting Chrome with remote debugging on port 9223...
start chrome.exe --remote-debugging-port=9223 --user-data-dir="%TEMP%\chrome-debug-9223"
echo Chrome started on port 9223
pause
