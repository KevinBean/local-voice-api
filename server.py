"""
Local Voice API — FastAPI server
Routes:
  GET  /health
  GET  /v1/models
  POST /v1/transcribe        multipart audio → {text, language}
  POST /v1/chat              JSON {messages, model?, provider?} → {response}
  POST /v1/speak             JSON {text, voice?, speed?} → audio/wav
  POST /v1/converse          multipart audio + form fields → {transcript, response, audio(base64)}
  POST /v1/converse/stream   multipart audio + form fields → NDJSON stream (sentence-by-sentence TTS)
"""
import base64
import io
import json
import re
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
    word_timestamps: Optional[bool] = Form(False),
):
    audio_bytes = await audio.read()
    result = await stt.transcribe(audio_bytes, language, word_timestamps=word_timestamps)
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

    print(f"[converse] history={len(history_list)} msgs, total={len(messages)} msgs")

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


# ── Streaming converse ─────────────────────────────────────────────────────

# Sentence boundary: split after . ! ? … (optionally followed by " ' ) ])
# then whitespace. Uses alternation to keep lookbehind fixed-width.
_SENT_RE = re.compile(
    r'(?:(?<=[.!?…])|(?<=[.!?…]["\')\]]))\s+'
)


def _split_first_sentence(text: str):
    """Return (first_sentence, remainder) if a sentence boundary exists, else (None, text)."""
    m = _SENT_RE.search(text)
    if m:
        return text[:m.start()].strip(), text[m.end():].strip()
    return None, text


@app.post("/v1/converse/stream")
async def converse_stream(
    audio: UploadFile = File(...),
    history: str = Form("[]"),
    system_prompt: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
):
    """Streaming STT → LLM → TTS pipeline. Returns NDJSON lines."""
    timing = {}

    # 1. Transcribe (must complete before streaming)
    t0 = time.perf_counter()
    audio_bytes = await audio.read()
    transcript_result = await stt.transcribe(audio_bytes)
    transcript = transcript_result["text"]
    timing["stt_ms"] = int((time.perf_counter() - t0) * 1000)

    if not transcript:
        async def _empty():
            yield json.dumps({"type": "transcript", "text": ""}) + "\n"
            yield json.dumps({"type": "done", "timing": timing}) + "\n"
        return StreamingResponse(_empty(), media_type="application/x-ndjson")

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

    print(f"[converse/stream] history={len(history_list)} msgs, total={len(messages)} msgs")

    async def _generate():
        nonlocal timing

        # Emit transcript immediately
        yield json.dumps({"type": "transcript", "text": transcript}) + "\n"

        # Stream LLM tokens, buffer into sentences, TTS each sentence
        sentence_buffer = ""
        full_response = ""
        sent_count = 0
        llm_t0 = time.perf_counter()
        first_token_time = None
        tts_total_ms = 0

        async for token in llm.chat_stream(messages, provider=provider or None):
            if first_token_time is None:
                first_token_time = time.perf_counter()
            sentence_buffer += token
            full_response += token

            # Try to extract complete sentences
            while True:
                sentence, remainder = _split_first_sentence(sentence_buffer)
                if sentence is None:
                    break
                sentence_buffer = remainder
                sent_count += 1

                tts_t0 = time.perf_counter()
                audio_data = await tts.speak(sentence)
                tts_total_ms += int((time.perf_counter() - tts_t0) * 1000)

                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                yield json.dumps({
                    "type": "sentence",
                    "index": sent_count,
                    "text": sentence,
                    "audio": audio_b64,
                }) + "\n"

        llm_ms = int((time.perf_counter() - llm_t0) * 1000)

        # Flush remaining text
        if sentence_buffer.strip():
            sent_count += 1
            tts_t0 = time.perf_counter()
            audio_data = await tts.speak(sentence_buffer.strip())
            tts_total_ms += int((time.perf_counter() - tts_t0) * 1000)

            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            yield json.dumps({
                "type": "sentence",
                "index": sent_count,
                "text": sentence_buffer.strip(),
                "audio": audio_b64,
            }) + "\n"

        timing["llm_ms"] = llm_ms
        timing["tts_ms"] = tts_total_ms
        timing["total_ms"] = timing["stt_ms"] + llm_ms + tts_total_ms

        yield json.dumps({
            "type": "done",
            "response": full_response,
            "timing": timing,
        }) + "\n"

        print(f"[converse/stream] STT={timing['stt_ms']}ms  LLM={llm_ms}ms  "
              f"TTS={tts_total_ms}ms  total={timing['total_ms']}ms  "
              f"sentences={sent_count}")

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
