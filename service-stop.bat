@echo off
REM Local Voice API — Stop Service
REM Kills uvicorn and its child processes on port 8601.

echo Stopping Local Voice API...

REM Find the main process listening on port 8601
set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8601 ^| findstr LISTENING') do (
    set FOUND=1
    echo Found PID %%a on port 8601

    REM Kill child processes first (uvicorn spawns multiprocessing workers)
    for /f "tokens=2" %%c in ('wmic process where "ParentProcessId=%%a" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
        echo   Killing child PID %%c
        taskkill /PID %%c /F >nul 2>&1
    )

    REM Kill the main process
    echo   Killing main PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

REM Also stop the scheduled task if running
schtasks /end /tn "LocalVoiceAPI" >nul 2>&1

if %FOUND%==0 (
    echo Nothing was running on port 8601.
) else (
    echo Done.
)
