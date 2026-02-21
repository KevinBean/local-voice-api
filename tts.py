"""
Local Voice API — TTS module
Primary: Kokoro (zero-cost, high-quality neural TTS)
Fallback: edge-tts (Microsoft Azure voices, free but requires internet)
"""
import asyncio
import io
import os
import shutil
import tempfile
from typing import Optional

import config


async def speak(
    text: str,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
) -> bytes:
    """Synthesize text → WAV bytes."""
    v = voice or config.TTS_VOICE
    s = speed if speed is not None else config.TTS_SPEED

    try:
        return await _speak_kokoro(text, v, s)
    except Exception as exc:
        print(f"[TTS] Kokoro failed ({exc}), falling back to edge-tts")
        return await _speak_edge(text, v, s)


# ── Kokoro (primary) ─────────────────────────────────────────────────────────

_kokoro_instance = None

_KOKORO_BASE_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
)
_KOKORO_MODEL_FILE  = "kokoro-v1.0.onnx"
_KOKORO_VOICES_FILE = "voices-v1.0.bin"


def _get_kokoro():
    """Lazy-load Kokoro, auto-downloading model files from GitHub releases on first use."""
    global _kokoro_instance
    if _kokoro_instance is None:
        import urllib.request
        from pathlib import Path
        from kokoro_onnx import Kokoro  # type: ignore

        cache_dir = Path.home() / ".cache" / "kokoro-onnx"
        cache_dir.mkdir(parents=True, exist_ok=True)

        model_path  = cache_dir / _KOKORO_MODEL_FILE
        voices_path = cache_dir / _KOKORO_VOICES_FILE

        for fname, fpath in [(_KOKORO_MODEL_FILE, model_path), (_KOKORO_VOICES_FILE, voices_path)]:
            if not fpath.exists():
                # Download to temp file first, then atomic rename to avoid corrupt partial files
                tmp_path = fpath.with_suffix(".tmp")
                print(f"[TTS] Downloading {fname} ...")
                try:
                    urllib.request.urlretrieve(_KOKORO_BASE_URL + fname, tmp_path)
                    tmp_path.rename(fpath)
                    print(f"[TTS] Downloaded {fname} ({fpath.stat().st_size // 1024 // 1024} MB)")
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise

        _kokoro_instance = Kokoro(str(model_path), str(voices_path))
        print("[TTS] Kokoro-ONNX loaded.")
    return _kokoro_instance


async def _speak_kokoro(text: str, voice: str, speed: float) -> bytes:
    import numpy as np
    import soundfile as sf

    def _synth():
        kokoro = _get_kokoro()
        samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format="WAV")
        buf.seek(0)
        return buf.read()

    return await asyncio.to_thread(_synth)


# ── Edge-TTS (fallback) ──────────────────────────────────────────────────────

# Mapping from Kokoro voice names to edge-tts neural voices
_EDGE_VOICE_MAP = {
    "af_heart":    "en-US-AriaNeural",
    "af_bella":    "en-US-JennyNeural",
    "af_sarah":    "en-US-SaraNeural",
    "am_adam":     "en-US-GuyNeural",
    "am_michael":  "en-US-ChristopherNeural",
    "bf_emma":     "en-GB-SoniaNeural",
    "bf_isabella": "en-GB-LibbyNeural",
    "bm_george":   "en-GB-RyanNeural",
    "bm_lewis":    "en-GB-ThomasNeural",
}


async def _speak_edge(text: str, voice: str, speed: float) -> bytes:
    import edge_tts  # type: ignore

    edge_voice = _EDGE_VOICE_MAP.get(voice, "en-US-AriaNeural")

    # edge-tts rate: "+10%" means 10% faster
    rate_pct = int((speed - 1.0) * 100)
    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

    communicate = edge_tts.Communicate(text, edge_voice, rate=rate_str)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = tmp.name
    wav_path = mp3_path.replace(".mp3", ".wav")

    try:
        await communicate.save(mp3_path)

        # Convert mp3 → wav (24 kHz mono) using ffmpeg (async to avoid blocking event loop)
        ffmpeg = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with code {proc.returncode}")

        with open(wav_path, "rb") as f:
            return f.read()
    finally:
        for p in (mp3_path, wav_path):
            if os.path.exists(p):
                os.unlink(p)
