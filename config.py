"""
Local Voice API — Configuration
All settings are driven by environment variables with sensible defaults.
"""
import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8601"))

# ── STT (faster-whisper) ──────────────────────────────────────────────────────
WHISPER_MODEL   = os.getenv("WHISPER_MODEL",   "base")     # tiny/base/small/medium/large-v3
WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE",  "cuda")     # cuda or cpu
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "float16")  # float16 / int8

# ── LLM (swappable) ───────────────────────────────────────────────────────────
LLM_PROVIDER    = os.getenv("LLM_PROVIDER",    "ollama")   # "ollama" or "openai"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3.1:latest")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY",  "")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL",    "gpt-4o-mini")

# ── TTS (Kokoro + edge-tts fallback) ─────────────────────────────────────────
TTS_VOICE = os.getenv("TTS_VOICE", "af_heart")
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))

VERSION = "1.0.0"
