@echo off
echo ========================================
echo Test Dual Output Pipeline voi Word (Simple)
echo ========================================
echo.
echo Tac vu don gian:
echo - Go tieu de
echo - Go noi dung
echo - Luu file
echo.
echo Nhan Enter de bat dau...
pause

cd /d "%~dp0"
call .venv\Scripts\activate.bat

python os_pipeline_dual_output.py --word --task "Viet tieu de 'Huong dan su dung Word', xuong dong, viet noi dung 'Day la huong dan co ban', xuong dong, viet 'Cam on ban da doc', sau do luu file" --output workspace/dual_output_word_simple --name word_simple --max-steps 15

echo.
echo ========================================
echo Kiem tra ket qua tai:
echo workspace/dual_output_word_simple/
echo - word_simple_final.mp4 (Video)
echo - word_simple.docx (Tutorial Document)
echo - word_simple.pdf (Tutorial PDF)
echo - screenshots/ (Anh chup man hinh)
echo ========================================
pause
