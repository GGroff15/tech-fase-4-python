import logging
from typing import Any, Optional, Dict
from transformers import pipeline

_pipeline = None
_logger = logging.getLogger("yolo_rest.audio.ser")


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    device = 0 if (hasattr(__import__("torch"), "cuda") and __import__("torch").cuda.is_available()) else -1

    try:
        _pipeline = pipeline(
            task="audio-classification",
            model="superb/wav2vec2-base-superb-er",
            device=device,
        )
    except Exception as e:
        _logger.error("failed loading SER pipeline: %s", e)
        _pipeline = None

    return _pipeline


def predict_emotion(wav_path: str) -> Optional[Dict[str, Any]]:
    """Return {'label': str, 'score': float} or None on failure/not-available."""
    p = _get_pipeline()
    if p is None:
        return None

    try:
        out = p(wav_path, top_k=1)
        if isinstance(out, list) and out:
            first = out[0]
            label = first.get("label")
            score = float(first.get("score", 0.0))
            return {"label": label, "score": score}
    except Exception as e:
        _logger.exception("SER inference failed: %s", e)

    return None
