@echo off
REM Script chay Streamlit UI voi venv

echo Starting Streamlit UI...
echo.

REM Kich hoat venv
call venv\Scripts\activate.bat

REM Chay Streamlit
streamlit run src/app.py

pause
