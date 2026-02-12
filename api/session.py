import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from aiortc import RTCDataChannel

logger = logging.getLogger("yolo_rest.api.session")


class Session:
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.created_at = time.time()
        self.closed_at: float | None = None
        self.data_channel: "RTCDataChannel | None" = None
        logger.info(f"Session created: {correlation_id}")

    def attach_data_channel(self, channel: "RTCDataChannel") -> None:
        self.data_channel = channel
        logger.info(f"Data channel attached to session: {self.correlation_id}, label={channel.label}")

    def close(self):
        if self.data_channel and getattr(self.data_channel, "readyState", "") != "closed":
            try:
                self.data_channel.close()
            except Exception:
                pass
        self.closed_at = time.time()
        duration = self.closed_at - self.created_at
        logger.info(f"Session closed: {self.correlation_id}, duration={duration:.2f}s")


class SessionRegistry:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, correlation_id: str) -> Session:
        session = Session(correlation_id)
        self._sessions[correlation_id] = session
        logger.info(f"Session registered: {correlation_id}, active_sessions={len(self._sessions)}")
        return session

    def get(self, correlation_id: str) -> Session | None:
        session = self._sessions.get(correlation_id)
        if session is None:
            logger.info(f"Session not found in registry: {correlation_id}")
        return session

    def close(self, correlation_id: str):
        session = self._sessions.pop(correlation_id, None)
        if session:
            session.close()
            logger.info(f"Session removed from registry: {correlation_id}, remaining_sessions={len(self._sessions)}")

    def all(self):
        return list(self._sessions.values())
