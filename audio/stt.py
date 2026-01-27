"""Vosk-based speech-to-text helpers.

Provides a small, synchronous API for transcribing WAV bytes using Vosk.

Functions:
- `transcribe_bytes(wav_bytes) -> Optional[str]` : return transcript or None on error
- `async_transcribe_bytes(...)` : async wrapper using `asyncio.to_thread`

This module uses `LazyModelLoader` so model loading is attempted once and
failures are logged but do not crash import-time.
"""

import json
import logging
import os
import wave
from typing import Optional
from vosk import Model

from vosk import KaldiRecognizer


logger = logging.getLogger("yolo_rest.audio.stt")

VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", os.path.join("models", "vosk-model-small"))


def _load_vosk_model():
    if not os.path.exists(VOSK_MODEL_PATH):
        raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")

    logger.info("Loading Vosk model from %s", VOSK_MODEL_PATH)
    return Model(VOSK_MODEL_PATH)


try:
    VOSK_MODEL = _load_vosk_model()
except Exception as e:  # fatal on startup
    logger.exception("Failed to load Vosk model on startup: %s", e)
    raise RuntimeError(f"Failed to load Vosk model: {e}")


def get_vosk_model():
    """Return the loaded Vosk model (guaranteed to be available on success)."""
    return VOSK_MODEL


def transcribe_bytes(wav_file: str) -> Optional[str]:
    """Transcribe WAV bytes and return transcript text or None on failure.

    Expects a valid WAV file (PCM). The function will attempt basic conversions
    (multi-channel -> mono, different sample widths) using `audioop`.
    """
    model = get_vosk_model()
    if model is None:
        logger.debug("Vosk model not available; cannot transcribe")
        return None

    try:
        with wave.open(wav_file, "rb") as wf:
            framerate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        rec = KaldiRecognizer(model, framerate)

        chunk_size = 4000
        idx = 0
        while idx < len(frames):
            chunk = frames[idx : idx + chunk_size]
            rec.AcceptWaveform(chunk)
            idx += chunk_size

        res_json = rec.FinalResult()
        res = json.loads(res_json)
        text = res.get("text", "")
        return text if text else None

    except FileNotFoundError:
        logger.exception("Vosk model missing while transcribing")
        return None
    except wave.Error:
        logger.exception("Invalid WAV data provided to transcribe_bytes")
        return None
    except Exception:
        logger.exception("Unexpected error during transcription")
        return None