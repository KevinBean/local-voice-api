@echo off
REM Local Voice API — Check Status

echo Checking Local Voice API status...
echo.

REM Check if port 8601 is in use
netstat -aon | findstr :8601 | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
    echo [RUNNING] Port 8601 is active.
    echo.
    curl -s http://localhost:8601/health 2>nul
    if %errorlevel% neq 0 (
        echo [WARNING] Port is open but /health did not respond.
    )
) else (
    echo [STOPPED] Nothing listening on port 8601.
)
echo.

REM Check Task Scheduler status
echo Task Scheduler:
schtasks /query /tn "LocalVoiceAPI" /fo list 2>nul | findstr /i "Status"
if %errorlevel% neq 0 (
    echo   Task "LocalVoiceAPI" not found in Task Scheduler.
)
