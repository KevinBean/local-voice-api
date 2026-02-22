@echo off
REM Local Voice API — Background Service
REM Called by service-launcher.vbs (hidden window) or Task Scheduler.
REM No --reload (production mode), logs to file.

cd /d "%~dp0"

REM ── Environment ─────────────────────────────────────────────────────────────
set PORT=8601
set HOST=0.0.0.0
set LLM_PROVIDER=ollama
set WHISPER_MODEL=base
set WHISPER_DEVICE=cuda
set WHISPER_COMPUTE=float16
set OLLAMA_MODEL=llama3.1:8b
set TTS_VOICE=af_heart
set TTS_SPEED=1.0
set PATH=C:\ffmpeg\bin;%PATH%

REM ── Logging ─────────────────────────────────────────────────────────────────
set LOGFILE=%~dp0local-voice-api.log

echo [%date% %time%] Starting Local Voice API on port %PORT%... >> "%LOGFILE%"

REM ── Launch (production mode, no file watcher) ──────────────────────────────
python -m uvicorn server:app --host %HOST% --port %PORT% >> "%LOGFILE%" 2>&1
