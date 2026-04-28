@echo off
echo Starting Excel and testing coordinates...
echo.

start excel

timeout /t 3 /nobreak >nul

python test_excel_coordinates.py

pause
