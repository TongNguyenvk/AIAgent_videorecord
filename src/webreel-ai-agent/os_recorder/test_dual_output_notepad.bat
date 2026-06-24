@echo off
echo ========================================
echo Test OS Pipeline Dual Output - Notepad
echo ========================================
echo.
echo Test nay se:
echo 1. Mo Notepad tu dong
echo 2. Agent do duong va sinh plan
echo 3. Quay video
echo 4. Chup hinh man hinh moi buoc
echo 5. Tao document DOCX va PDF tu dong
echo.
echo Bam phim bat ky de bat dau...
pause

call .venv\Scripts\activate.bat
python os_pipeline_dual_output.py --notepad --task "Go text 'Hello World' vao Notepad" --name "demo_notepad_dual" --voice "banmai"

echo.
echo ===============m tra output tai:
echo workspace\pipeline_dual_output\
echo ========================================
pause
