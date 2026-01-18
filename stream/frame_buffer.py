import asyncio
from typing import Any
from av import Packet
from av.frame import Frame

# Constants
BUFFER_MAX_SIZE = 1


class FrameBuffer:
    """A simple async frame buffer with drop-replace behavior.

    Uses an asyncio.Queue with maxsize=1. When a new frame arrives and the
    queue is full, the existing frame is discarded and replaced with the new
    one to prioritize the most recent frame (low-latency policy).
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=BUFFER_MAX_SIZE)
        self.dropped_count: int = 0

    async def put(self, frame: Frame | Packet | bytes) -> bool:
        """Put a frame into the buffer, dropping the existing one if full.

        Returns True if an existing frame was dropped, False otherwise.
        """
        was_dropped = False
        if self._queue.full():
            try:
                _ = self._queue.get_nowait()
                self.dropped_count += 1
                was_dropped = True
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(frame)
        return was_dropped

    async def get(self) -> Frame | Packet | bytes:
        """Get the most recent frame (blocks until available)."""
        return await self._queue.get()

    def empty(self) -> bool:
        """Check if buffer is empty."""
        return self._queue.empty()
