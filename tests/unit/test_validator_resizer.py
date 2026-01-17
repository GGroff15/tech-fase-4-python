import pytest
import numpy as np
import cv2

from preprocessing.validator import validate_resolution
from preprocessing.resizer import resize_to_720p


def make_image(h, w):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_validate_within_limits():
    img = make_image(720, 1280)
    assert validate_resolution(img)


def test_validate_over_limit_and_resize():
    img = make_image(2000, 2000)
    assert not validate_resolution(img)
    r = resize_to_720p(img)
    h, w = r.shape[:2]
    assert h <= 720 and w <= 1280
