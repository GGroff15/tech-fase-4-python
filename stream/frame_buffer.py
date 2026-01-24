import asyncio
from typing import Any
from av import Packet
from av.frame import Frame
from abc import ABC, abstractmethod

# Constants
BUFFER_MAX_SIZE = 1


class BaseBuffer(ABC):
    """Abstract base for async buffers used by processors.

    Implementations must provide `put`, `get` and `empty` methods. This
    allows processors to operate polymorphically over different buffer types.
    """

    @abstractmethod
    async def put(self, frame: Any) -> bool:
        """Put an item into the buffer. Return True if an existing item was dropped."""

    @abstractmethod
    async def get(self) -> Any:
        """Get the next item from the buffer (awaitable)."""

    @abstractmethod
    def empty(self) -> bool:
        """Return True if the buffer is empty."""


class FrameBuffer(BaseBuffer):
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


class AudioBuffer(BaseBuffer):
    """An async buffer optimized for audio frames.

    - Larger queue to hold incoming audio frames.
    - `put` drops the oldest frame when full (drop-replace policy).
    - `get` returns a single frame (awaitable).
    - `get_many` collects up to `max_items` frames or waits until `timeout` elapses.
    """

    def __init__(self, maxsize: int = 1024) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.dropped_count: int = 0

    async def put(self, frame) -> bool:
        """Put a frame into the buffer, dropping oldest if full.

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

    async def get(self):
        """Get a single frame (await until available)."""
        return await self._queue.get()

    async def get_many(self, max_items: int = 50, timeout: float = 0.5):
        """Collect up to `max_items` frames.

        Waits until at least one frame is available, then tries to gather more without blocking
        longer than `timeout` seconds for additional frames.
        """
        items = []
        try:
            first = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return items

        items.append(first)

        # quickly drain up to max_items-1 without awaiting long
        for _ in range(max_items - 1):
            try:
                nxt = self._queue.get_nowait()
                items.append(nxt)
            except asyncio.QueueEmpty:
                break

        return items

    def empty(self) -> bool:
        return self._queue.empty()
