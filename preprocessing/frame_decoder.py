from av import VideoFrame
import cv2
import numpy as np


def decode_image(frame: VideoFrame | bytes) -> np.ndarray:
    """Decode WebRTC Frame or JPEG/PNG bytes to NumPy array."""
    if isinstance(frame, VideoFrame):
        # Convert aiortc Frame to NumPy array
        return frame.to_ndarray(format="bgr24")
    else:
        # Decode JPEG/PNG bytes
        nparr = np.frombuffer(frame, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image format")
        return img
