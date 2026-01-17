from typing import Tuple
import cv2


def validate_resolution(img) -> bool:
    """Return True if image resolution is within allowed bounds (<=1280x720)."""
    h, w = img.shape[:2]
    return h <= 720 and w <= 1280


def get_resolution(img) -> Tuple[int, int]:
    h, w = img.shape[:2]
    return w, h


def estimate_blur_score(img) -> float:
    """Estimate blur using variance of Laplacian. Higher is sharper.

    Returns a float where lower values indicate blurrier images.
    """
    if img is None:
        return 0.0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        var = float(lap.var())
        return var
    except Exception:
        return 0.0


def is_blurry(img, threshold: float = 100.0) -> bool:
    """Return True if image is considered blurry.

    Default threshold 100.0 is a reasonable starting point; tune per dataset.
    """
    return estimate_blur_score(img) < threshold
