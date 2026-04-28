@echo off
echo ========================================
echo Test Dual Output Pipeline voi Word
echo ========================================
echo.
echo Tac vu: Tao van ban bao cao co dinh dang
echo - Tao tieu de
echo - Them noi dung
echo - Dinh dang chu (Bold, Italic)
echo - Luu file
echo.
echo Nhan Enter de bat dau...
pause

cd /d "%~dp0"
call .venv\Scripts\activate.bat

python os_pipeline_dual_output.py --word --task "Tao van ban bao cao voi tieu de 'Bao cao thang 3', them noi dung 'Day la noi dung bao cao', dinh dang tieu de thanh Bold va Italic, sau do luu file voi ten 'BaoCaoThang3.docx'" --output workspace/dual_output_word --name word_demo --max-steps 20

echo.
echo ========================================
echo Kiem tra ket qua tai:
echo workspace/dual_output_word/
echo ========================================
pause
