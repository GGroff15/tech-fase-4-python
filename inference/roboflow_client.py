import asyncio
import os
from typing import Any, Dict, List, Optional

import cv2
import httpx
import numpy as np

from config.constants import DEFAULT_ROBOFLOW_CONFIDENCE as DEFAULT_CONFIDENCE
from config.constants import DEFAULT_USE_LOCAL_FALLBACK, IMAGE_ENCODING_FORMAT
from config.constants import ROBOFLOW_HTTP_TIMEOUT_SEC as DEFAULT_HTTP_TIMEOUT
from inference.fallback import LocalYoloFallback


class RoboflowConfig:
    """Configuration for Roboflow inference client."""

    def __init__(
        self,
        model_url: Optional[str] = None,
        api_key: Optional[str] = None,
        confidence: float = DEFAULT_CONFIDENCE,
    ):
        self.model_url = model_url or os.getenv("ROBOFLOW_MODEL_URL")
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        self.confidence = float(os.getenv("ROBOFLOW_CONFIDENCE", str(confidence)))
        self.use_local_fallback = (
            os.getenv("ROBOFLOW_USE_LOCAL_FALLBACK", DEFAULT_USE_LOCAL_FALLBACK).lower()
            == "true"
        )

    def is_configured(self) -> bool:
        """Check if Roboflow API is properly configured."""
        return bool(self.model_url and self.api_key)

    def get_request_params(self) -> Dict[str, Any]:
        """Get HTTP request parameters for Roboflow API."""
        return {"api_key": self.api_key, "confidence": int(self.confidence * 100)}


class ImageEncoder:
    """Handles image encoding for API requests."""

    @staticmethod
    def encode_to_jpeg(image: np.ndarray) -> bytes | None:
        """Encode numpy array image to JPEG bytes."""
        success, buffer = cv2.imencode(IMAGE_ENCODING_FORMAT, image)
        if not success:
            return None
        return buffer.tobytes()


class DetectionParser:
    """Parses API responses into standardized detection format."""

    @staticmethod
    def parse_predictions(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Roboflow API response into detection list."""
        predictions = []
        for index, prediction in enumerate(response_data.get("predictions", [])):
            parsed = DetectionParser._parse_single_prediction(prediction, index)
            if parsed:
                predictions.append(parsed)
        return predictions

    @staticmethod
    def _parse_single_prediction(
        prediction: Dict[str, Any], detection_id: int
    ) -> Dict[str, Any]:
        """Parse a single prediction into standard format."""
        bbox = DetectionParser._extract_bbox(prediction)
        class_name = DetectionParser._extract_class_name(prediction)
        confidence = float(prediction.get("confidence", 0.0))
        type_confidence = float(prediction.get("class_confidence", confidence))

        return {
            "id": detection_id,
            "cls": class_name,
            "bbox": [float(b) if b is not None else 0.0 for b in bbox],
            "confidence": confidence,
            "type_confidence": type_confidence,
        }

    @staticmethod
    def _extract_bbox(prediction: Dict[str, Any]) -> List[float]:
        """Extract bounding box from prediction."""
        bbox = prediction.get("bbox")
        if bbox:
            return bbox
        return [
            prediction.get("x"),
            prediction.get("y"),
            prediction.get("width"),
            prediction.get("height"),
        ]

    @staticmethod
    def _extract_class_name(prediction: Dict[str, Any]) -> str:
        """Extract class name from prediction."""
        return (
            prediction.get("class")
            or prediction.get("cls")
            or prediction.get("label")
            or "unknown"
        )


class MockDetectionGenerator:
    """Generates mock detections for testing."""

    @staticmethod
    async def generate(image: np.ndarray) -> List[Dict[str, Any]]:
        """Generate deterministic mock detection."""
        await asyncio.sleep(0)
        try:
            height, width = image.shape[:2]
        except Exception:
            return []

        if width <= 50:
            return []

        center_x = width / 2
        center_y = height / 2
        bbox_width = min(100, width * 0.3)
        bbox_height = min(100, height * 0.3)
        x = max(0, center_x - bbox_width / 2)
        y = max(0, center_y - bbox_height / 2)

        return [
            {
                "id": 1,
                "cls": "cut",
                "bbox": [float(x), float(y), float(bbox_width), float(bbox_height)],
                "confidence": 0.75,
                "type_confidence": 0.6,
            }
        ]


class RoboflowClient:
    """Async Roboflow client with fallback to local inference.

    Configuration via environment variables:
    - ROBOFLOW_API_KEY
    - ROBOFLOW_MODEL_URL (e.g. https://detect.roboflow.com/{model}/{version})
    - ROBOFLOW_CONFIDENCE (float 0.0-1.0, default 0.5)
    - ROBOFLOW_USE_LOCAL_FALLBACK (true/false, default true)
    """

    def __init__(
        self,
        model_url: Optional[str] = None,
        api_key: Optional[str] = None,
        confidence: float = DEFAULT_CONFIDENCE,
    ):
        self.config = RoboflowConfig(model_url, api_key, confidence)
        self._client: Optional[httpx.AsyncClient] = None
        self._fallback: Optional[LocalYoloFallback] = None

    def _ensure_client(self) -> None:
        """Lazily initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT)

    async def predict(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Return a list of detections from the image.

        Falls back to local inference or mock if Roboflow is unavailable.
        """
        if not self.config.is_configured():
            return await self._predict_with_fallback(image)

        return await self._predict_with_roboflow(image)

    async def _predict_with_roboflow(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Predict using Roboflow API."""
        image_bytes = ImageEncoder.encode_to_jpeg(image)
        if not image_bytes:
            return []

        self._ensure_client()
        try:
            response = await self._client.post(
                self.config.model_url,
                files={"file": image_bytes},
                params=self.config.get_request_params(),
            )
            response.raise_for_status()
            return DetectionParser.parse_predictions(response.json())
        except Exception:
            return await self._predict_with_fallback(image)

    async def _predict_with_fallback(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Predict using local fallback or mock."""
        if self.config.use_local_fallback:
            local_prediction = await self._try_local_fallback(image)
            if local_prediction is not None:
                return local_prediction

        return await MockDetectionGenerator.generate(image)

    async def _try_local_fallback(
        self, image: np.ndarray
    ) -> List[Dict[str, Any]] | None:
        """Try to use local YOLO fallback."""
        try:
            if self._fallback is None:
                self._fallback = LocalYoloFallback()
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._fallback.predict, image)
        except Exception:
            return None

    async def close(self) -> None:
        """Close HTTP client resources."""
        if self._client is not None:
            await self._client.aclose()


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
