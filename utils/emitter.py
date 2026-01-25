"""Helpers for safe event emission and DataChannel wrapping.

Provides `safe_emit` to call arbitrary emitters (sync or async) with
consistent error handling and `DataChannelWrapper` to encapsulate data
channel ready-state checks and sending JSON safely.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("yolo_rest.utils.emitter")


async def safe_emit(
    emitter: Callable[[Any], Any],
    event: Any,
    logger: Optional[logging.Logger] = None,
    session_id: Optional[str] = None,
) -> None:
    """Call `emitter(event)` safely: await if awaitable and log exceptions.

    `emitter` may be an async function or a sync callable. Exceptions are
    logged and swallowed to avoid crashing processing loops.
    """
    lg = logger or logger
    try:
        result = emitter(event)
        if inspect.isawaitable(result):
            await result
    except Exception as e:
        try:
            if lg:
                lg.error("safe_emit failed: %s", e, extra={"session_id": session_id})
        except Exception:
            # ensure we never raise from logging
            pass


class DataChannelWrapper:
    """Wraps a datachannel-like object providing `is_open` and `send_json`.

    The wrapped `channel` is expected to have `.readyState` and `.send()`.
    This wrapper centralizes readiness checks and exception handling.
    """

    def __init__(self, channel: Any):
        self._channel = channel

    def is_open(self) -> bool:
        try:
            return getattr(self._channel, "readyState", None) == "open"
        except Exception:
            return False

    def send_json(self, payload: Any) -> None:
        try:
            if not self.is_open():
                return
            if isinstance(payload, (dict, list)):
                data = json.dumps(payload)
            elif isinstance(payload, str):
                data = payload
            else:
                data = json.dumps(payload)
            self._channel.send(data)
        except Exception as e:
            try:
                logger.error("DataChannel send failed: %s", e)
            except Exception:
                pass
