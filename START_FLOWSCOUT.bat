@echo off
REM Redirect to bat\START_FLOWSCOUT.bat (canonical launcher folder)
cd /d "%~dp0"
if exist "%~dp0bat\START_FLOWSCOUT.bat" (
  call "%~dp0bat\START_FLOWSCOUT.bat"
) else (
  echo Missing bat\START_FLOWSCOUT.bat
  pause
  exit /b 1
)
