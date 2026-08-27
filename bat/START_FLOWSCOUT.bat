@echo off
title FlowScout Launcher
color 0A
cd /d "%~dp0.."

echo.
echo ============================================================
echo    FlowScout Pro - Starting
echo ============================================================
echo Project: %cd%
echo URL:     http://127.0.0.1:8000/
echo.

set "PYEXE=%cd%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo ERROR: Missing venv Python at %PYEXE%
  echo Run: python -m venv .venv
  pause
  exit /b 1
)
if not defined IBKR_ENABLED set IBKR_ENABLED=0

set OK=0

rem Always restart the server so Python edits take effect. The dashboard
rem now reconnects without a visible reload, so this is not disruptive.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Stopping old process on port 8000 ^(PID %%P^)...
    taskkill /F /PID %%P >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo [1/3] Starting server window...
start "FlowScout Server" /D "%cd%" "%PYEXE%" zerodte_websocket_server.py

echo [2/3] Waiting for server ^(up to 60s^)...
for /L %%I in (1,1,60) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if not errorlevel 1 (
        set OK=1
        goto :open_browser
    )
    timeout /t 1 /nobreak >nul
)

echo.
echo SERVER DID NOT START - check the "FlowScout Server" window for errors.
pause
exit /b 1

:open_browser
echo [3/3] Opening browser ^(reuses existing tab/window^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%cd%\OPEN_FLOWSCOUT_BROWSER.ps1" -Url "http://127.0.0.1:8000/"

echo.
echo Done. Keep the "FlowScout Server" window open while you trade.
echo This launcher closes in 3 seconds...
timeout /t 3 /nobreak >nul
exit /b 0
