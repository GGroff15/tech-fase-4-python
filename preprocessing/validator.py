from typing import Tuple

import cv2
import numpy as np

from config.constants import DEFAULT_BLUR_THRESHOLD
from config.constants import MAX_IMAGE_HEIGHT as MAX_HEIGHT
from config.constants import MAX_IMAGE_WIDTH as MAX_WIDTH


def validate_resolution(image: np.ndarray) -> bool:
    """Return True if image resolution is within allowed bounds (<=1280x720)."""
    height, width = image.shape[:2]
    return height <= MAX_HEIGHT and width <= MAX_WIDTH


def get_resolution(image: np.ndarray) -> Tuple[int, int]:
    """Get image resolution as (width, height) tuple."""
    height, width = image.shape[:2]
    return width, height


def estimate_blur_score(image: np.ndarray) -> float:
    """Estimate blur using variance of Laplacian. Higher is sharper.

    Returns a float where lower values indicate blurrier images.
    """
    if image is None:
        return 0.0
    try:
        grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(grayscale_image, cv2.CV_64F)
        variance = float(laplacian.var())
        return variance
    except Exception:
        return 0.0


def is_blurry(image: np.ndarray, threshold: float = DEFAULT_BLUR_THRESHOLD) -> bool:
    """Return True if image is considered blurry.

    Default threshold 100.0 is a reasonable starting point; tune per dataset.
    """
    return estimate_blur_score(image) < threshold
