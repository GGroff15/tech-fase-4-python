import cv2


def resize_to_720p(img):
    """Resize image to fit within 1280x720 while preserving aspect ratio."""
    h, w = img.shape[:2]
    max_h, max_w = 720, 1280
    if h <= max_h and w <= max_w:
        return img
    scale = min(max_h / h, max_w / w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
