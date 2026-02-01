import asyncio
import logging
from typing import Any, Dict, Optional
from .emotion_adapter import normalize_emotion

from utils.loader import LazyModelLoader, get_torch_device

_logger = logging.getLogger("yolo_rest.audio.ser")


# Mapping used by prithivMLmods/Speech-Emotion-Classification
# Normalized to lowercase to match existing code expectations.
ID2LABEL = {
    "0": "neutral",
    "1": "calm",
    "2": "happy",
    "3": "sad",
    "4": "angry",
    "5": "fearful",
    "6": "disgust",
    "7": "surprised",
}


class _PrithivWrapper:
    """Small wrapper around the HF model+processor exposing `predict(wav_path)`.

    The wrapper keeps the model on the requested device and performs audio
    loading/resampling on each call. It returns a dict mapping labels to scores.
    """

    def __init__(self, model, processor, device):
        self.model = model
        self.processor = processor
        self.device = device

    def predict_scores(self, wav_path: str) -> Optional[Dict[str, float]]:
        try:
            import librosa
            import torch

            # load and resample to 16kHz (model expects 16k)
            speech, sr = librosa.load(wav_path, sr=16000)

            inputs = self.processor(
                speech,
                sampling_rate=sr,
                return_tensors="pt",
                padding=True,
            )

            # Move tensors to device
            device = torch.device("cuda:0") if self.device >= 0 else torch.device("cpu")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=1).squeeze(0).cpu().numpy()

            # map to label names
            scores: Dict[str, float] = {}
            for i, p in enumerate(probs.tolist()):
                label = ID2LABEL.get(str(i), str(i))
                scores[label] = float(round(p, 6))

            return scores
        except Exception as e:
            _logger.exception("Prithiv model inference failed: %s", e)
            return None


def _make_pipeline():
    """Lazy factory that loads the prithivMLmods model and its feature extractor.

    Returns an instance of `_PrithivWrapper` or `None` on failure.
    """
    try:
        from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
        import torch

        model_name = "prithivMLmods/Speech-Emotion-Classification"


        device_id = get_torch_device()
        device_str = f"cuda:{device_id}" if device_id >= 0 else "cpu"

        model = Wav2Vec2ForSequenceClassification.from_pretrained(model_name)
        processor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)

        # Use getattr to call `.to` so some static checkers don't confuse bound-method typing
        torch_device = torch.device(device_str)
        getattr(model, "to")(torch_device)

        return _PrithivWrapper(model, processor, device_id)
    except Exception as e:
        _logger.exception("failed loading prithivMLmods SER model: %s", e)
        return None


# Lazy loader for the SER model; loading attempted on first use.
_pipeline_loader = LazyModelLoader(_make_pipeline, name="ser_prithiv")


def predict_emotion(wav_path: str) -> Optional[Dict[str, Any]]:
    """Return {'label': str, 'score': float} or None on failure/not-available.

    Keeps backwards-compatible top-label API. Adds `probabilities` map when
    available to provide full distribution without breaking callers.
    """
    wrapper = _pipeline_loader.get()
    if wrapper is None:
        return None

    try:
        scores = wrapper.predict_scores(wav_path)
        if not scores:
            return None

        # pick top label
        top_label = max(scores, key=scores.get)
        top_score = float(scores[top_label])

        raw = {"label": top_label, "score": top_score, "probabilities": scores}
        normalized = normalize_emotion(raw)
        return normalized
    except Exception as e:
        _logger.exception("SER inference failed: %s", e)
        return None


async def preload(app=None):
    """Preload the SER model off the event loop (called on server startup).

    This triggers the lazy loader in a thread to download / initialize the
    model so the first real inference isn't delayed by model download.
    """
    try:
        result = await asyncio.to_thread(_pipeline_loader.get)
        if _pipeline_loader.is_available():
            _logger.info("SER pipeline preloaded successfully: %s", type(result).__name__ if result is not None else "None")
        else:
            err = _pipeline_loader.get_error()
            _logger.warning("SER pipeline preload completed but model unavailable: %s", err)
    except Exception as e:
        _logger.exception("SER preload failed: %s", e)
