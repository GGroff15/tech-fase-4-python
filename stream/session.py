import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger("yolo_rest.session")


class StreamSession:
    """Represents a streaming session lifecycle and basic auditing.

    This lightweight session object tracks start/end times and frame counts.
    Higher-level components (frame buffer/processor) should call `record_frame()`
    when a frame is accepted for processing.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        idle_timeout: int = 30,
        correlation_id: Optional[str] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.start_time = time.time()
        self.end_time = None
        # Frames processed (keeps previous semantics)
        self.frame_count = 0
        # Audio-specific counters
        self.audio_frame_count = 0
        self.audio_seconds = 0.0
        # Total frames received from client
        self.total_received = 0
        # Frames dropped due to buffer replacement
        self.dropped_count = 0
        # Total detections emitted
        self.detection_count = 0
        self.idle_timeout = idle_timeout
        self.last_activity = self.start_time
        logger.info(
            "session.created",
            extra={"session_id": self.session_id, "correlation_id": self.correlation_id},
        )

    def record_frame(self) -> None:
        self.frame_count += 1
        self.last_activity = time.time()

    def record_audio(self, frames: int = 1, seconds: float = 0.0) -> None:
        """Record audio frames/seconds received and touch last activity."""
        self.audio_frame_count += frames
        try:
            self.audio_seconds += float(seconds)
        except Exception:
            pass
        self.last_activity = time.time()

    def record_received(self) -> None:
        self.total_received += 1
        self.last_activity = time.time()

    def record_dropped(self, n: int = 1) -> None:
        self.dropped_count += n
        self.last_activity = time.time()

    def record_detection(self, n: int = 1) -> None:
        self.detection_count += n

    def is_idle(self) -> bool:
        return (time.time() - self.last_activity) > self.idle_timeout

    def close(self) -> dict:
        self.end_time = time.time()
        summary = {
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "start_time": int(self.start_time * 1000),
            "end_time": int(self.end_time * 1000),
            "frame_count": self.frame_count,
            "audio_frame_count": self.audio_frame_count,
            "audio_seconds": self.audio_seconds,
        }
        logger.info("session.closed", extra=summary)
        return summary
