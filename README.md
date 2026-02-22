# Local Voice API

A standalone HTTP server that provides STT → LLM → TTS in a single `/v1/converse` endpoint.
Designed as a zero-cost replacement for the OpenAI Realtime API (~$0.30/min) for TalkBuddy.

## Cost comparison

| Mode | STT | LLM | TTS | Est. cost |
|------|-----|-----|-----|-----------|
| OpenAI Realtime | bundled | bundled | bundled | ~$0.30/min |
| **Full local** | faster-whisper | Ollama Llama | Kokoro | **$0** |
| Semi-local | faster-whisper | OpenAI gpt-4o-mini | Kokoro | ~$0.002/turn |

## Requirements

- Python 3.10+
- CUDA GPU recommended (falls back to CPU)
- ffmpeg on PATH (for edge-tts fallback)
- Ollama running locally (`ollama serve`)

## Quick start

```bat
# Install dependencies
pip install -r requirements.txt

# Start (double-click or run):
start.bat
```

Server starts at `http://localhost:8601`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server status + config |
| GET | `/v1/models` | Available models |
| POST | `/v1/transcribe` | Audio file → text |
| POST | `/v1/chat` | Messages → text response |
| POST | `/v1/speak` | Text → WAV audio stream |
| POST | `/v1/converse` | Audio → transcript + response + audio (main endpoint) |

### `/v1/converse` — main endpoint

**Form fields:**
- `audio` (file) — audio recording (webm/wav/mp3)
- `history` (JSON string) — conversation history `[{role, content}, ...]`
- `system_prompt` (string, optional) — system/persona instructions
- `provider` (string, optional) — `"ollama"` or `"openai"` (overrides server default)

**Response JSON:**
```json
{
  "transcript": "what the user said",
  "response":   "the AI's reply text",
  "audio":      "<base64 WAV>"
}
```

## Configuration

All settings are environment variables (see `config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` / `large-v3` |
| `WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` |
| `OLLAMA_MODEL` | `llama3.1:8b` | Any model pulled in Ollama |
| `OPENAI_API_KEY` | — | Required for `openai` provider |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model ID |
| `TTS_VOICE` | `af_heart` | Kokoro voice name |
| `TTS_SPEED` | `1.0` | Speech rate (0.5 – 2.0) |

## Kokoro voices

American English: `af_heart`, `af_bella`, `af_sarah`, `am_adam`, `am_michael`
British English: `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`

## Running as a Windows Service

The API can run automatically at login with no visible window.

### Quick setup

```bat
REM 1. Register Task Scheduler entry (one-time, requires admin for schtasks /sc onlogon)
powershell -ExecutionPolicy Bypass -File create-task.ps1

REM 2. Or use Startup folder (no admin needed — already done by create-shortcut.ps1)
powershell -ExecutionPolicy Bypass -File create-shortcut.ps1
```

### Management commands

| Script | Purpose |
|--------|---------|
| `service-start.bat` | Start the API (via Task Scheduler or directly) |
| `service-stop.bat` | Stop the running API |
| `service-status.bat` | Check if API is running + health check |
| `start.bat` | Dev mode with `--reload` (visible terminal) |

### How it works

- `service-launcher.vbs` runs `service.bat` with a hidden window (no console flash)
- `service.bat` sets env vars and launches `uvicorn` in production mode (no `--reload`)
- Logs are written to `local-voice-api.log`
- Auto-starts at user logon via Windows Startup folder shortcut

### Remote access (Tailscale)

From MacBook: `curl http://100.91.167.57:8601/health`

## TalkBuddy integration

In TalkBuddy Settings → **Connection Mode** → select **Local Voice API**.
Enter `http://localhost:8601` (or `http://100.91.167.57:8601` from MacBook via Tailscale).
Click **Test Connection** → green = ready.
Start Practice → hold mic button → release to send.
