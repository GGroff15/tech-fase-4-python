"""Helpers for safe event emission and DataChannel wrapping.

Provides `safe_emit` to call arbitrary emitters (sync or async) with
consistent error handling and `DataChannelWrapper` to encapsulate data
channel ready-state checks and sending JSON safely.
"""

import logging
import requests
from typing import Any

from api.session import Session
from config.constants import EVENT_FORWARD_BASE_URL, API_KEY

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
        requests.post(url, json=payload.to_dict(), headers=headers)
    except Exception as e:
        logger.error("http_post_event failed for %s: %s", url, e)