"""
Local Voice API — STT module (faster-whisper)
Lazy-loads the model on first use to keep startup fast.
"""
import asyncio
import io
from typing import Optional

import config

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        compute = config.WHISPER_COMPUTE
        # CPU doesn't support float16 — fall back to int8
        if config.WHISPER_DEVICE == "cpu" and compute == "float16":
            compute = "int8"

        print(f"[STT] Loading Whisper model '{config.WHISPER_MODEL}' "
              f"on {config.WHISPER_DEVICE} ({compute})...")
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=compute,
        )
        print("[STT] Model loaded.")
    return _model


async def transcribe(
    audio_bytes: bytes,
    language: Optional[str] = None,
    word_timestamps: bool = False,
) -> dict:
    """Transcribe raw audio bytes → {text, language}.

    When *word_timestamps* is True the response also contains a ``words``
    list with per-word start/end times and confidence (probability).
    """

    def _run():
        model = _get_model()
        audio_io = io.BytesIO(audio_bytes)
        kwargs: dict = {}
        if language:
            kwargs["language"] = language
        if word_timestamps:
            kwargs["word_timestamps"] = True
        segments, info = model.transcribe(audio_io, **kwargs)

        text_parts = []
        words = []
        for seg in segments:
            text_parts.append(seg.text)
            if word_timestamps and seg.words:
                for w in seg.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3),
                    })

        result = {"text": " ".join(text_parts).strip(), "language": info.language}
        if word_timestamps:
            result["words"] = words
        return result

    return await asyncio.to_thread(_run)
