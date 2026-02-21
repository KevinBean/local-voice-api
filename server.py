"""
Local Voice API — FastAPI server
Routes:
  GET  /health
  GET  /v1/models
  POST /v1/transcribe   multipart audio → {text, language}
  POST /v1/chat         JSON {messages, model?, provider?} → {response}
  POST /v1/speak        JSON {text, voice?, speed?} → audio/wav
  POST /v1/converse     multipart audio + form fields → {transcript, response, audio(base64)}
"""
import base64
import io
import json
import time
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
import llm
import stt
import tts

app = FastAPI(title="Local Voice API", version=config.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    provider: Optional[str] = None


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    speed: Optional[float] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": config.VERSION,
        "llm_provider": config.LLM_PROVIDER,
        "whisper_model": config.WHISPER_MODEL,
    }


@app.get("/v1/models")
async def list_models():
    return {
        "models": [
            {"id": config.OLLAMA_MODEL,  "provider": "ollama"},
            {"id": config.OPENAI_MODEL,  "provider": "openai"},
        ]
    }


@app.post("/v1/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    audio_bytes = await audio.read()
    result = await stt.transcribe(audio_bytes, language)
    return result


@app.post("/v1/chat")
async def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]
    response_text = await llm.chat(
        messages,
        model=request.model,
        provider=request.provider,
    )
    return {"response": response_text}


@app.post("/v1/speak")
async def speak(request: SpeakRequest):
    audio_bytes = await tts.speak(request.text, voice=request.voice, speed=request.speed)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")


@app.post("/v1/converse")
async def converse(
    audio: UploadFile = File(...),
    history: str = Form("[]"),
    system_prompt: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
):
    """Full STT → LLM → TTS pipeline in a single HTTP call.

    Returns:
        transcript: what the user said
        response:   the AI's text reply
        audio:      base64-encoded WAV of the AI's speech
        timing:     per-stage milliseconds {stt_ms, llm_ms, tts_ms, total_ms}
    """
    timing = {}

    # 1. Transcribe
    t0 = time.perf_counter()
    audio_bytes = await audio.read()
    transcript_result = await stt.transcribe(audio_bytes)
    transcript = transcript_result["text"]
    timing["stt_ms"] = int((time.perf_counter() - t0) * 1000)

    # Handle empty transcription (silence / noise)
    if not transcript:
        return {
            "transcript": "",
            "response": "I didn't catch that. Could you try again?",
            "audio": "",
            "timing": timing,
        }

    # 2. Build message list
    messages: list = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    try:
        history_list = json.loads(history)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid history JSON: {exc}")

    messages.extend(history_list)
    messages.append({"role": "user", "content": transcript})

    # 3. LLM
    t0 = time.perf_counter()
    response_text = await llm.chat(
        messages,
        provider=provider or None,
    )
    timing["llm_ms"] = int((time.perf_counter() - t0) * 1000)

    # 4. TTS
    t0 = time.perf_counter()
    audio_response = await tts.speak(response_text)
    audio_b64 = base64.b64encode(audio_response).decode("utf-8")
    timing["tts_ms"] = int((time.perf_counter() - t0) * 1000)

    timing["total_ms"] = timing["stt_ms"] + timing["llm_ms"] + timing["tts_ms"]

    print(f"[converse] STT={timing['stt_ms']}ms  LLM={timing['llm_ms']}ms  "
          f"TTS={timing['tts_ms']}ms  total={timing['total_ms']}ms")

    return {
        "transcript": transcript,
        "response": response_text,
        "audio": audio_b64,
        "timing": timing,
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
