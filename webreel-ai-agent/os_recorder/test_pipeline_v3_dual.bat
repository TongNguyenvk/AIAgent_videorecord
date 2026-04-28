@echo off
REM Test OS Pipeline V3 with Dual Output
REM Tao video + DOCX + PDF tu mot lan chay

echo ========================================
echo Test OS Pipeline V3 Dual Output
echo ========================================
echo.

python os_pipeline_v3_dual.py --notepad --task "Gõ text 'Hello World from V3 Dual Pipeline', xuống dòng, gõ 'This is a test'" --name "test_v3_dual" --voice "banmai" --max-steps 15

echo.
echo ========================================
echo Test hoan tat!
echo Kiem tra thu muc: workspace/pipeline_v3_dual/
echo - test_v3_dual_final.mp4 (video co audio)
echo - test_v3_dual.docx (document tutorial)
echo - test_v3_dual.pdf (PDF tutorial)
echo ========================================
pause
