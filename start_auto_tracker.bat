@echo off
echo ========================================
echo Automated Market Tracker
echo ========================================
echo.
echo This will run continuously and track markets automatically
echo - Runs at market open (9:30 AM)
echo - Runs hourly during market hours (10 AM - 3 PM)
echo - Runs at market close (4:00 PM)
echo - Runs after hours summary (6:00 PM)
echo.
echo Press Ctrl+C to stop
echo.
echo ========================================
echo.

cd /d "%~dp0"

REM Try simple tracker first (no external deps)
python simple_auto_tracker.py

pause

