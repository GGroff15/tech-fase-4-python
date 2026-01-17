import os
from typing import List, Dict, Any, Optional

import cv2
import asyncio
import numpy as np
import httpx
import asyncio


from inference.fallback import LocalYoloFallback


class RoboflowClient:
    """Async Roboflow client with fallback to a lightweight mock.

    Configuration via environment variables:
    - ROBOFLOW_API_KEY
    - ROBOFLOW_MODEL_URL (e.g. https://detect.roboflow.com/{model}/{version})
    - ROBOFLOW_CONFIDENCE (float 0.0-1.0, default 0.5)
    """

    def __init__(self, model_url: Optional[str] = None, api_key: Optional[str] = None, confidence: float = 0.5):
        self.model_url = model_url or os.getenv("ROBOFLOW_MODEL_URL")
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        self.confidence = float(os.getenv("ROBOFLOW_CONFIDENCE", str(confidence)))
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)

    async def predict(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Return a list of detections in Roboflow-like format.

        Each detection dict will include: class, bbox [x,y,w,h], confidence, type_confidence
        Coordinates from Roboflow are returned in absolute pixels; caller may normalize.
        """
        # If Roboflow not configured, try local fallback if available, else mock
        if not self.model_url or not self.api_key:
            # try local fallback when configured
            use_local = os.getenv("ROBOFLOW_USE_LOCAL_FALLBACK", "true").lower() == "true"
            if use_local:
                try:
                    local = LocalYoloFallback()
                    # local.predict is sync; run in thread to avoid blocking
                    loop = asyncio.get_running_loop()
                    return await loop.run_in_executor(None, local.predict, image)
                except Exception:
                    pass
            return await self._mock_infer(image)

        # encode image as jpeg
        success, buf = cv2.imencode('.jpg', image)
        if not success:
            return []
        image_bytes = buf.tobytes()

        self._ensure_client()
        params = {"api_key": self.api_key, "confidence": int(self.confidence * 100)}
        try:
            resp = await self._client.post(self.model_url, files={"file": image_bytes}, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            # On error, fall back to mock to keep stream alive
            return await self._mock_infer(image)

        # Parse predictions into expected dict format
        preds = []
        for i, p in enumerate(data.get("predictions", [])):
            # Roboflow uses center/width/height or x,y,w,h depending on export; handle common cases
            bbox = p.get("bbox") or [p.get("x"), p.get("y"), p.get("width"), p.get("height")]
            preds.append(
                {
                    "id": i,
                    "cls": p.get("class") or p.get("cls") or p.get("label"),
                    "bbox": [float(b) if b is not None else 0.0 for b in bbox],
                    "confidence": float(p.get("confidence", 0.0)),
                    "type_confidence": float(p.get("class_confidence", p.get("confidence", 0.0))),
                }
            )

        return preds

    async def close(self):
        if self._client is not None:
            await self._client.aclose()

    async def _mock_infer(self, image: np.ndarray) -> List[Dict[str, Any]]:
        # deterministic lightweight mock used when Roboflow is not configured
        await asyncio.sleep(0)  # type: ignore[name-defined]
        try:
            h, w = image.shape[:2]
        except Exception:
            return []

        if w > 50:
            cx = w / 2
            cy = h / 2
            bbox_w = min(100, w * 0.3)
            bbox_h = min(100, h * 0.3)
            x = max(0, cx - bbox_w / 2)
            y = max(0, cy - bbox_h / 2)
            detection = {
                "id": 1,
                "cls": "cut",
                "bbox": [float(x), float(y), float(bbox_w), float(bbox_h)],
                "confidence": 0.75,
                "type_confidence": 0.6,
            }
            return [detection]

        return []


__all__ = ["RoboflowClient"]


# Backwards-compatible helper used by existing code
_default_client: Optional[RoboflowClient] = None


def _get_default_client() -> RoboflowClient:
    global _default_client
    if _default_client is None:
        _default_client = RoboflowClient()
    return _default_client


async def infer_image(image: np.ndarray) -> List[Dict[str, Any]]:
    """Compatibility wrapper used by the pipeline (keeps previous function name)."""
    client = _get_default_client()
    return await client.predict(image)
