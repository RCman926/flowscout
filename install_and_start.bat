@echo off
echo Installing required packages...
pip install schedule

echo.
echo Starting automated tracker...
echo This will run in the background and track markets automatically.
echo.
echo To stop: Close this window or press Ctrl+C
echo.

cd /d "%~dp0"
python simple_auto_tracker.py

