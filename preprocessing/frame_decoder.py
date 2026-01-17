import cv2
import numpy as np


def decode_image(data: bytes):
    """Decode JPEG/PNG bytes into an OpenCV BGR image (numpy array).

    Raises ValueError if decoding fails.
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("failed to decode image")
    return img
