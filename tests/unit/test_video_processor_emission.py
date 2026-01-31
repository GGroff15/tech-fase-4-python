import pytest
from unittest.mock import Mock, AsyncMock

from stream.frame_buffer import VideoBuffer
from stream.frame_processor import VideoProcessor
from stream.session import StreamSession


class DummySession(StreamSession):
    def __init__(self):
        self.session_id = "sess-123"
        self.frame_count = 1234
        self.record_detection = Mock()
        self.record_frame = Mock()


class DummyBuffer(VideoBuffer):
    pass


@pytest.mark.asyncio
async def test_video_processor_emits_per_object_events():
    session = DummySession()
    buffer = DummyBuffer()
    vp = VideoProcessor(session, buffer)

    emitter = AsyncMock()

    detections = [
        {"id": 1, "cls": "person", "bbox": [0, 0, 10, 10], "confidence": 0.76123, "type_confidence": 0.5},
        {"id": 2, "cls": "knife", "bbox": [1, 1, 5, 5], "confidence": "0.3456", "type_confidence": 0.2},
    ]

    # Call the protected method directly to focus on emission behavior
    await vp._emit_detection_event(detections, quality_warning=None, emitter=emitter)

    # Metrics recorded
    session.record_detection.assert_called_once_with(2)
    session.record_frame.assert_called_once()

    # Emitter called once per detected object
    assert emitter.call_count == 2

    first_payload = emitter.call_args_list[0][0][0]
    assert first_payload["label"] == "person"
    assert round(first_payload["confidence"], 2) == pytest.approx(0.76)
    assert first_payload["frameIndex"] == session.frame_count

    second_payload = emitter.call_args_list[1][0][0]
    assert second_payload["label"] == "knife"
    assert round(second_payload["confidence"], 2) == pytest.approx(0.35)
    assert second_payload["frameIndex"] == session.frame_count
