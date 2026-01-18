import cv2
import numpy as np

# Constants
MAX_HEIGHT = 720
MAX_WIDTH = 1280
MIN_DIMENSION = 1


def resize_to_720p(image: np.ndarray) -> np.ndarray:
    """Resize image to fit within 1280x720 while preserving aspect ratio."""
    height, width = image.shape[:2]
    
    if height <= MAX_HEIGHT and width <= MAX_WIDTH:
        return image
    
    scale = min(MAX_HEIGHT / height, MAX_WIDTH / width)
    new_width = max(MIN_DIMENSION, int(width * scale))
    new_height = max(MIN_DIMENSION, int(height * scale))
    
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
