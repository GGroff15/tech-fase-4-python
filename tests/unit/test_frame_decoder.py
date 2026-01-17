import cv2
import numpy as np

from preprocessing.frame_decoder import decode_image


def make_jpeg_bytes():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()


def test_decode_jpeg():
    data = make_jpeg_bytes()
    img = decode_image(data)
    assert img is not None
    assert img.shape[0] == 100 and img.shape[1] == 200
