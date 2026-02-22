@echo off
REM Local Voice API — Manual Start
REM Starts the scheduled task (or launches directly if task doesn't exist).

echo Starting Local Voice API...

REM Try starting via Task Scheduler first
schtasks /run /tn "LocalVoiceAPI" >nul 2>&1
if %errorlevel%==0 (
    echo Started via Task Scheduler.
) else (
    echo Task Scheduler entry not found. Launching directly...
    wscript "%~dp0service-launcher.vbs"
)

REM Wait a moment then check
ping -n 4 127.0.0.1 >nul 2>&1
curl -s http://localhost:8601/health >nul 2>&1
if not errorlevel 1 (
    echo [OK] API is running on port 8601.
) else (
    echo [WAIT] API is still starting up - model loading takes ~10s.
    echo        Run service-status.bat to check later.
)
