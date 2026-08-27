@echo off
title FlowScout unattended
cd /d "%~dp0"
set UNATTENDED=1
set PAPER_AUTO_ARMED=true
set "PYEXE=%cd%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%P >nul 2>&1
)
timeout /t 2 /nobreak >nul
"%PYEXE%" -c "from paper_arm_state import paper_arm_state; paper_arm_state.set_armed(True); print('paper ARMED')"
"%PYEXE%" zerodte_websocket_server.py
