import numpy as np
from av import VideoFrame


def decode_image(frame: VideoFrame) -> np.ndarray:
    """Decode WebRTC Frame or JPEG/PNG bytes to NumPy array."""
    return frame.to_ndarray(format="bgr24")
