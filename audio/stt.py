"""Vosk-based speech-to-text helpers.

Provides a synchronous API for transcribing WAV files using Vosk.

Functions:
- `transcribe_bytes(wav_path) -> Optional[str]` : transcribe file and return text or None
- `transcribe_with_partials(wav_path)` : get both partial and final results
- `get_vosk_model()` : get the loaded model instance

Performance optimizations:
- Larger chunk sizes (32KB) for better throughput
- Lazy model loading for faster startup
- Partial results for real-time feedback

Optimal window: 2-3 seconds for real-time STT
"""

import json
import logging
import os
import wave
from typing import Optional

logger = logging.getLogger("yolo_rest.audio.stt")

VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", os.path.join("models", "vosk-model-small"))

# Performance tuning: 8KB chunks for responsive partial results
# (32KB is too large for short 2-3s windows)
VOSK_CHUNK_SIZE = 8000

# Lazy-loaded model
_VOSK_MODEL = None
_VOSK_MODEL_LOADED = False


def _load_vosk_model():
    from vosk import Model, SetLogLevel
    
    # Suppress Vosk verbose logging
    SetLogLevel(-1)
    
    if not os.path.exists(VOSK_MODEL_PATH):
        raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")

    logger.info("Loading Vosk model from %s", VOSK_MODEL_PATH)
    return Model(VOSK_MODEL_PATH)


def get_vosk_model():
    """Return the loaded Vosk model, loading lazily on first call."""
    global _VOSK_MODEL, _VOSK_MODEL_LOADED
    
    if not _VOSK_MODEL_LOADED:
        try:
            _VOSK_MODEL = _load_vosk_model()
            logger.info("Vosk model loaded successfully")
        except Exception as e:
            logger.error("Failed to load Vosk model: %s", e)
            _VOSK_MODEL = None
        _VOSK_MODEL_LOADED = True
    
    return _VOSK_MODEL


def transcribe_bytes(wav_file: str) -> Optional[str]:
    """Transcribe a WAV file and return transcript text or None on failure.

    Args:
        wav_file: Path to a WAV file (should be 16kHz mono for best results)
        
    Returns:
        Transcript text or None if transcription failed or no speech detected
    """
    from vosk import KaldiRecognizer
    
    model = get_vosk_model()
    if model is None:
        logger.warning("Vosk model not available; cannot transcribe")
        return None

    try:
        with wave.open(wav_file, "rb") as wf:
            framerate = wf.getframerate()
            
            rec = KaldiRecognizer(model, framerate)
            rec.SetWords(False)  # Faster without word timestamps
            
            # Process in chunks
            while True:
                data = wf.readframes(VOSK_CHUNK_SIZE)
                if not data:
                    break
                rec.AcceptWaveform(data)

            res_json = rec.FinalResult()
            res = json.loads(res_json)
            text = res.get("text", "").strip()
            
            return text if text else None

    except FileNotFoundError:
        logger.error("WAV file not found: %s", wav_file)
        return None
    except wave.Error as e:
        logger.error("Invalid WAV file %s: %s", wav_file, e)
        return None
    except Exception as e:
        logger.exception("Unexpected error during transcription: %s", e)
        return None