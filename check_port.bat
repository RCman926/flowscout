@echo off
echo Checking what's using port 8000...
netstat -ano | findstr ":8000"
echo.
echo If you see a PID (Process ID), you can kill it with:
echo taskkill /PID [PID_NUMBER] /F
pause

