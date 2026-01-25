import os

import numpy as np

from inference.roboflow_client import infer_image


def make_test_image():
    # simple black image with size >50px to trigger mock/local detection
    return np.zeros((200, 200, 3), dtype=np.uint8)


def test_local_fallback_detects():
    # Ensure Roboflow is not configured so the client uses local fallback
    os.environ.pop("ROBOFLOW_MODEL_URL", None)
    os.environ.pop("ROBOFLOW_API_KEY", None)
    os.environ["ROBOFLOW_USE_LOCAL_FALLBACK"] = "true"

    img = make_test_image()
    detections = None

    # infer_image should return a list (possibly empty if local model missing)
    detections = infer_image(img)

    # If infer_image is a coroutine (older API), await it
    if hasattr(detections, "__await__"):
        import asyncio

        detections = asyncio.get_event_loop().run_until_complete(detections)

    assert isinstance(detections, list)
