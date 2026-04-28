@echo off
echo ============================================================
echo Running Excel Pipeline Test
echo ============================================================
echo.

cd /d "%~dp0"

echo Activating virtual environment...
call ..\.venv\Scripts\activate.bat

echo.
echo Starting pipeline with Excel...
echo Task: Nhap chu 'Bao cao doanh thu' vao o B2, sau do nhap so '500' vao o C2.
echo.

python os_pipeline.py --excel --task "Nhập chữ 'Báo cáo doanh thu' vào ô B2, sau đó nhập số '500' vào ô C2."

echo.
echo ============================================================
echo Pipeline completed!
echo ============================================================
pause
