@echo off
title FlowScout - Market Review
cd /d "%~dp0.."
set "PYEXE=%cd%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
  echo Missing venv: %PYEXE%
  pause
  exit /b 1
)
echo Running %days%-day market review (default 5)...
"%PYEXE%" -c "from market_review import build_review; import json; r=build_review(5); print(json.dumps(r, indent=2, default=str))"
echo.
echo Saved to session_recap when server runs /api/market-review
pause
