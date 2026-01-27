import asyncio
from abc import ABC, abstractmethod
import time
from typing import List

from av import AudioFrame, VideoFrame
from av.frame import Frame

from config.constants import FRAME_BUFFER_MAX_SIZE


class BaseBuffer(ABC):
    """Abstract base for async buffers used by processors.

    Implementations must provide `put`, `get` and `empty` methods. This
    allows processors to operate polymorphically over different buffer types.
    """

    @abstractmethod
    async def put(self, frame: Frame) -> bool:
        """Put an item into the buffer. Return True if an existing item was dropped."""

    @abstractmethod
    async def get(self) -> Frame:
        """Get the next item from the buffer (awaitable)."""

    @abstractmethod
    def empty(self) -> bool:
        """Return True if the buffer is empty."""

    async def _put_with_drop_oldest(self, queue: asyncio.Queue, frame: Frame) -> Frame | None:
        """Helper: put `frame` into `queue`, dropping the oldest item if full.

        Returns True if an existing item was dropped.
        """
        dropped_frame = None
        if queue.full():
            try:
                dropped_frame = queue.get_nowait()
                # increment dropped_count if present on self
                if hasattr(self, "dropped_count"):
                    try:
                        self.dropped_count += 1
                    except Exception:
                        # defensive: if attribute exists but is not int, ignore
                        pass
            except asyncio.QueueEmpty:
                pass
        await queue.put(frame)
        
        if dropped_frame:
            return dropped_frame
        
        return None


class BaseAudioBuffer(BaseBuffer):
    """Abstract base for audio frame buffers used by audio processors.

    Extends BaseBuffer to indicate specialization for audio frames.
    """

    def __init__(self, maxsize: int = 1024) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.duration: float = 0.0
        
    async def put(self, queue: asyncio.Queue, frame: AudioFrame) -> AudioFrame | None:
        self.duration += frame.samples / frame.sample_rate
        dropped = await self._put_with_drop_oldest(queue, frame)
        
        if dropped and isinstance(dropped, AudioFrame):
            self.duration -= dropped.samples / dropped.sample_rate
            af = dropped
            return af
        return None

    async def get_many(self, retrive_duration: float = 5, timeout: float = 0.5) -> List[AudioFrame]:
        """Return a list of AudioFrames

        Args:
            retrive_duration (float, optional): Audio duration to retrieve in seconds. Defaults to 5.
            timeout (float, optional): Timeout for retrieving frames in seconds. Defaults to 0.5.

        Returns:
            List[AudioFrame]: List of AudioFrames retrieved from the buffer.
        """
        items: List[AudioFrame] = []
        accumulated_duration: float = 0.0
        
        timeout_expiration = time.time() + timeout
        while accumulated_duration < retrive_duration and time.time() < timeout_expiration:
            try:
                frame: AudioFrame = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                items.append(frame)
                accumulated_duration += frame.samples / frame.sample_rate
            except asyncio.TimeoutError:
                break

        return items
    
    def get_size(self) -> int:
        """Get current size of the buffer."""
        return self._queue.qsize()
    
    async def get(self) -> AudioFrame:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()


class AudioBufferBroadcast(BaseBuffer):
    buffers: List[BaseAudioBuffer]

    def __init__(self, buffers: List[BaseAudioBuffer]) -> None:
        self.buffers = buffers
        
    async def get(self) -> AudioFrame:
        raise NotImplementedError

    def empty(self) -> bool:
        raise NotImplementedError

    async def put(self, frame: Frame) -> bool:
        if not isinstance(frame, AudioFrame):
            raise ValueError("AudioBufferBroadcast only accepts AudioFrame instances.")
        
        dropped_any: bool = False
        for buffer in self.buffers:
            dropped = await buffer.put(buffer._queue, frame)
            if dropped:
                return True
        return dropped_any


class AudioEmotionBuffer(BaseAudioBuffer):
    """Buffer for audio emotion detection.

    - Larger queue to hold incoming audio frames (defaults to 1024).
    - Supports `put`, `get`, and `get_many` for windowed aggregation.
    - Tracks `dropped_count` when items are dropped due to full queue.
    """

    def __init__(self, maxsize: int = 1024) -> None:
        super().__init__(maxsize=maxsize)


class SpeechToTextBuffer(BaseAudioBuffer):
    """Buffer optimized for speech-to-text consumers.

    - Smaller default queue (defaults to 1024) tuned for streaming/low-latency STT.
    - Provides `put` and `get` for single-item consumption and an optional
      `get_stream` async generator for consumers that want a continuous stream.
    - Also tracks `dropped_count`.
    """

    def __init__(self, maxsize: int = 1024) -> None:
        super().__init__(maxsize=maxsize)

class VideoBuffer(BaseBuffer):
    """A simple async frame buffer with drop-replace behavior.

    Uses an asyncio.Queue with maxsize=1. When a new frame arrives and the
    queue is full, the existing frame is discarded and replaced with the new
    one to prioritize the most recent frame (low-latency policy).
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=FRAME_BUFFER_MAX_SIZE)
        self.dropped_count: int = 0

    async def put(self, frame: VideoFrame) -> VideoFrame | None:
        """Put a frame into the buffer, dropping the existing one if full.

        Returns True if an existing frame was dropped, False otherwise.
        """
        dropped = await self._put_with_drop_oldest(self._queue, frame)
        
        if dropped and isinstance(dropped, VideoFrame):
            self.dropped_count += 1
            vf = dropped
            return vf
        
        return None

    async def get(self) -> VideoFrame:
        """Get the most recent frame (blocks until available)."""
        return await self._queue.get()

    def empty(self) -> bool:
        """Check if buffer is empty."""
        return self._queue.empty()