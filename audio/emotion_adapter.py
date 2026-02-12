import logging
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger("yolo_rest.audio.emotion_adapter")

CANONICAL_LABELS = [
    "neutral",
    "happy",
    "sad",
    "angry",
    "fearful",
    "calm",
    "disgusted",
    "surprised",
]

# Numeric id mapping based on the model used in the project
ID_MAP = {
    "0": "neutral",
    "1": "calm",
    "2": "happy",
    "3": "sad",
    "4": "angry",
    "5": "fearful",
    "6": "disgusted",
    "7": "surprised",
}

# Common synonyms -> canonical
SYNONYMS = {
    "disgust": "disgusted",
}


def canonical_label(raw_label: Optional[str]) -> Optional[str]:
    """Map a raw label (id, lowercase/uppercase name, synonym) to a canonical lowercase label.

    Returns None if the label is falsy or unrecognized.
    """
    if not raw_label:
        return None

    s = str(raw_label).strip().lower()
    if not s:
        return None

    # numeric id keys
    if s in ID_MAP:
        return ID_MAP[s]

    # direct canonical
    if s in CANONICAL_LABELS:
        return s

    # synonyms
    if s in SYNONYMS:
        return SYNONYMS[s]

    logger.info(f"Unrecognized emotion label: {raw_label}")
    return None


def map_probabilities(probs: Mapping[str, float]) -> Dict[str, float]:
    """Remap a probabilities mapping (any key style) to canonical lowercase labels.

    Missing canonical labels will be present with value 0.0.
    """
    out: Dict[str, float] = {k: 0.0 for k in CANONICAL_LABELS}

    for k, v in dict(probs).items():
        try:
            val = float(v)
        except Exception:
            continue

        cl = canonical_label(str(k))
        if cl is None:
            continue
        out[cl] = val

    return out


def normalize_emotion(input_value: Any) -> Optional[Dict[str, Any]]:
    """Normalize various model outputs into a predictable lowercase shape.

    Accepted inputs:
    - None -> returns None
    - str -> interpreted as a raw label name or id
    - Mapping with 'label'/'score' and optionally 'probabilities' (predict_emotion style)
    - Mapping of probabilities directly (label->score)

    Returns: {'label': <lowercase or None>, 'score': float, 'probabilities': {<lowercase>: float, ...}}
    """
    if input_value is None:
        return None

    # If a raw string label/id
    if isinstance(input_value, str):
        label = canonical_label(input_value)
        probs = map_probabilities({input_value: 1.0 if label is not None else 0.0})
        score = probs[label] if label is not None else 0.0
        return {"label": label, "score": float(score), "probabilities": probs}

    # If a mapping-like object
    if isinstance(input_value, Mapping):
        # If this already looks like the predict_emotion shape
        raw_label = None
        raw_score = None
        raw_probs = None

        if "probabilities" in input_value:
            raw_probs = input_value.get("probabilities")
        elif all(isinstance(v, (int, float)) for v in input_value.values()):
            # treat as probs mapping
            raw_probs = input_value

        raw_label = input_value.get("label") if "label" in input_value else None
        raw_score = input_value.get("score") if "score" in input_value else None

        probs = map_probabilities(raw_probs) if raw_probs is not None else {k: 0.0 for k in CANONICAL_LABELS}

        label = canonical_label(raw_label) if raw_label is not None else None
        if label is None:
            # pick highest probability if available
            max_label = max(probs, key=probs.get) if probs else None
            label = max_label if max_label and probs.get(max_label, 0.0) > 0.0 else None

        # choose score from probs if label present, else fallback to provided score or 0.0
        score = float(probs[label]) if (label is not None and label in probs) else (float(raw_score) if raw_score is not None else 0.0)

        return {"label": label, "score": score, "probabilities": probs}

    # Unsupported input type
    return None
