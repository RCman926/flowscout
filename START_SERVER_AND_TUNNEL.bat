@echo off
echo ============================================================
echo   FlowScout Pro - Starting Server and Cloudflare Tunnel
echo ============================================================
echo.

REM Start the server in a new window
REM Use %cd% to make it portable - works from any directory
start "FlowScout Server" cmd /k "cd /d %cd% && python zerodte_websocket_server.py"

REM Wait 5 seconds for server to start
echo Waiting for server to start...
timeout /t 5 /nobreak

REM Find cloudflared executable (check PATH first, then common locations)
set CLOUDFLARED_CMD=
where cloudflared.exe >nul 2>&1
if %ERRORLEVEL% == 0 (
    set CLOUDFLARED_CMD=cloudflared.exe
    echo Found cloudflared in PATH
) else (
    REM Check common installation locations
    if exist "C:\cloudflared\cloudflared-windows-amd64.exe" (
        set CLOUDFLARED_CMD=C:\cloudflared\cloudflared-windows-amd64.exe
        echo Found cloudflared at C:\cloudflared\
    ) else if exist "%USERPROFILE%\cloudflared\cloudflared-windows-amd64.exe" (
        set CLOUDFLARED_CMD=%USERPROFILE%\cloudflared\cloudflared-windows-amd64.exe
        echo Found cloudflared at %USERPROFILE%\cloudflared\
    ) else if exist "%LOCALAPPDATA%\cloudflared\cloudflared-windows-amd64.exe" (
        set CLOUDFLARED_CMD=%LOCALAPPDATA%\cloudflared\cloudflared-windows-amd64.exe
        echo Found cloudflared at %LOCALAPPDATA%\cloudflared\
    ) else if exist "%ProgramFiles%\cloudflared\cloudflared-windows-amd64.exe" (
        set CLOUDFLARED_CMD=%ProgramFiles%\cloudflared\cloudflared-windows-amd64.exe
        echo Found cloudflared at %ProgramFiles%\cloudflared\
    ) else (
        echo.
        echo ERROR: cloudflared not found!
        echo.
        echo Please install cloudflared from: https://github.com/cloudflare/cloudflared/releases
        echo Or add cloudflared to your PATH environment variable
        echo.
        pause
        exit /b 1
    )
)

REM Start Cloudflare tunnel in a new window
echo Starting Cloudflare tunnel...
start "Cloudflare Tunnel" cmd /k "%CLOUDFLARED_CMD% tunnel --url http://localhost:8000"

echo.
echo ============================================================
echo   Both windows should now be open!
echo   Copy the Cloudflare URL from the tunnel window
echo   Share it with your friends
echo ============================================================
echo.
pause

