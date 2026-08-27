@echo off
title FlowScout Pro - Server
cd /d "%~dp0"

echo.
echo ============================================================
echo   FlowScout Pro - Starting Server
echo ============================================================
echo.
echo Project: %cd%
echo URL:     http://localhost:8000/
echo.
echo Do NOT double-click zerodte_client_enhanced.html
echo Wait until this window says SERVER STARTED.
echo.

set "PYEXE=%cd%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

if not defined IBKR_ENABLED set IBKR_ENABLED=0

echo Using: %PYEXE%
echo.

for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Stopping old process on port 8000 ^(PID %%P^)...
    taskkill /F /PID %%P >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo Starting server in this window...
echo Press Ctrl+C to stop
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$py = '%PYEXE%';" ^
  "$p = Start-Process -FilePath $py -ArgumentList 'zerodte_websocket_server.py' -WorkingDirectory '%cd%' -NoNewWindow -PassThru;" ^
  "Write-Host '[INFO] Waiting for http://localhost:8000/ (up to 45s)...';" ^
  "$ok = $false;" ^
  "for ($i = 0; $i -lt 45; $i++) {" ^
  "  if ($p.HasExited) { break }" ^
  "  try {" ^
  "    $r = Invoke-WebRequest -Uri 'http://localhost:8000/' -UseBasicParsing -TimeoutSec 2;" ^
  "    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { $ok = $true; break }" ^
  "  } catch {}" ^
  "  $listen = netstat -ano | Select-String ':8000' | Select-String 'LISTENING';" ^
  "  if ($listen -and $i -gt 3) {" ^
  "    try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/' -UseBasicParsing -TimeoutSec 2; $ok = $true; break } catch {}" ^
  "  }" ^
  "  Start-Sleep -Seconds 1" ^
  "}" ^
  "if (-not $ok) {" ^
  "  Write-Host '';" ^
  "  Write-Host 'SERVER DID NOT START. Do NOT double-click the .html file.';" ^
  "  Write-Host 'Use START_FLOWSCOUT.bat after Python is working.';" ^
  "  if (-not $p.HasExited) { try { Stop-Process -Id $p.Id -Force } catch {} }" ^
  "  exit 1" ^
  "}" ^
  "Write-Host '';" ^
  "Write-Host 'SERVER STARTED — opening http://localhost:8000/?fresh=1';" ^
  "Start-Process 'http://localhost:8000/?fresh=1';" ^
  "Write-Host 'Leave this window open. Press Ctrl+C to stop.';" ^
  "try { Wait-Process -Id $p.Id } finally { if ($p -and -not $p.HasExited) { try { Stop-Process -Id $p.Id -Force } catch {} } }"

if errorlevel 1 (
    echo.
    echo Failed to start. Do not open the .html file by itself.
    pause
)
pause
