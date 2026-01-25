import cv2
import numpy as np

from config.constants import MAX_IMAGE_HEIGHT as MAX_HEIGHT
from config.constants import MAX_IMAGE_WIDTH as MAX_WIDTH
from config.constants import MIN_IMAGE_DIMENSION as MIN_DIMENSION


def resize_to_720p(image: np.ndarray) -> np.ndarray:
    """Resize image to fit within 1280x720 while preserving aspect ratio."""
    height, width = image.shape[:2]

    if height <= MAX_HEIGHT and width <= MAX_WIDTH:
        return image

    scale = min(MAX_HEIGHT / height, MAX_WIDTH / width)
    new_width = max(MIN_DIMENSION, int(width * scale))
    new_height = max(MIN_DIMENSION, int(height * scale))

    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
