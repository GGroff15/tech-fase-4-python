import logging
from typing import Any, Dict, Optional

from utils.loader import LazyModelLoader, get_torch_device

_logger = logging.getLogger("yolo_rest.audio.ser")


def _make_pipeline():
    try:
        from transformers import pipeline

        device = get_torch_device()
        return pipeline(
            task="audio-classification",
            model="superb/wav2vec2-base-superb-er",
            device=device,
        )
    except Exception as e:
        _logger.error("failed loading SER pipeline: %s", e)
        return None


# Lazy loader for the SER pipeline; loading attempted on first use.
_pipeline_loader = LazyModelLoader(_make_pipeline, name="ser_pipeline")


def predict_emotion(wav_path: str) -> Optional[Dict[str, Any]]:
    """Return {'label': str, 'score': float} or None on failure/not-available."""
    p = _pipeline_loader.get()
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
