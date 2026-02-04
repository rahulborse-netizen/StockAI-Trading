@echo off
echo ============================================================
echo AI Trading Dashboard
echo ============================================================
echo.
cd /d "%~dp0"
echo Current directory: %CD%
echo.
echo Starting web server...
echo Open your browser and go to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.
python run_web.py
pause
