@echo off
REM Local Voice API — Quick Start
REM Edit variables below to customise the server

set LLM_PROVIDER=ollama
set WHISPER_MODEL=base
set WHISPER_DEVICE=cuda
set WHISPER_COMPUTE=float16
set OLLAMA_MODEL=llama3.1:8b
set TTS_VOICE=af_heart
set TTS_SPEED=1.0

REM Uncomment and fill in to use OpenAI as the LLM provider:
REM set LLM_PROVIDER=openai
REM set OPENAI_API_KEY=sk-...
REM set OPENAI_MODEL=gpt-4o-mini

REM Add ffmpeg to PATH if not already present
set PATH=C:\ffmpeg\bin;%PATH%

echo Starting Local Voice API on port 8601 (dev mode)...
uvicorn server:app --host 0.0.0.0 --port 8601 --reload
pause
