"""Helpers for event emission over HTTP and WebRTC data channels."""

import asyncio
import json
import logging
import requests
from typing import Any

from api.session import Session
from config.constants import EVENT_FORWARD_BASE_URL, API_KEY, HTTP_REQUEST_TIMEOUT_SEC

logger = logging.getLogger("yolo_rest.utils.emitter")


def http_post_event(path: str, payload: Any, session: Session) -> None:
    """POST `payload` as JSON to `base_url + path`.

    This is best-effort: exceptions are logged and swallowed so callers
    (real-time processors) are not affected by transient HTTP errors.
    """

    url = f"{EVENT_FORWARD_BASE_URL.rstrip('/')}/events/{path.lstrip('/')}"
    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
            "X-Correlation-Id": session.correlation_id
            }
        requests.post(url, json=payload.to_dict(), headers=headers, timeout=HTTP_REQUEST_TIMEOUT_SEC)
    except Exception as e:
        logger.error("http_post_event failed for %s: %s", url, e)


class DataChannelWrapper:
    """Thread-safe JSON sender for an aiortc data channel."""

    def __init__(self, channel: Any, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self._channel = channel
        self._loop = loop or asyncio.get_running_loop()

    def _is_open(self) -> bool:
        return bool(self._channel) and getattr(self._channel, "readyState", "") == "open"

    def send_json(self, payload: Any) -> None:
        if not self._is_open():
            logger.debug("data channel not open; skipping send")
            return

        try:
            data = payload.to_dict() if hasattr(payload, "to_dict") else payload
            message = json.dumps(data)
        except Exception as e:
            logger.error("failed to serialize payload for data channel: %s", e)
            return

        try:
            self._loop.call_soon_threadsafe(self._channel.send, message)
        except Exception as e:
            logger.error("data channel send failed: %s", e)