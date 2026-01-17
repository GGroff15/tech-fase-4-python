import os
import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import app


def make_jpeg_bytes():
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()


def test_websocket_receive_detection(monkeypatch):
    # Enable dev-mode auth bypass for the test
    monkeypatch.setenv("DEV_MODE_DISABLE_AUTH", "true")

    client = TestClient(app)

    data = make_jpeg_bytes()

    with client.websocket_connect("/ws/analyze") as ws:
        ws.send_bytes(data)
        event = ws.receive_json()
        assert "session_id" in event
        assert "frame_index" in event
        assert "timestamp_ms" in event
        assert "has_wounds" in event
        assert "wounds" in event
