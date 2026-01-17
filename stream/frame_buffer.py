import asyncio
from typing import Any


class FrameBuffer:
    """A simple async frame buffer with drop-replace behavior.

    Uses an asyncio.Queue with maxsize=1. When a new frame arrives and the
    queue is full, the existing frame is discarded and replaced with the new
    one to prioritize the most recent frame (low-latency policy).
    """

    def __init__(self):
        self._queue = asyncio.Queue(maxsize=1)
        self.dropped_count = 0

    async def put(self, frame: Any) -> bool:
        """Put a frame into the buffer, dropping the existing one if full.

        Returns True if an existing frame was dropped, False otherwise.
        """
        dropped = False
        if self._queue.full():
            try:
                _ = self._queue.get_nowait()
                self.dropped_count += 1
                dropped = True
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(frame)
        return dropped

    async def get(self) -> Any:
        """Get the most recent frame (blocks until available)."""
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
