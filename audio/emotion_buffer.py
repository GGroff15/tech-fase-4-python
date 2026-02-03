from collections import deque


class EmotionAudioBuffer:
    def __init__(self, sample_rate=16_000, window_sec=1.0):
        self._bytes_per_sample = 2
        self._sample_rate = sample_rate
        self._window_sec = window_sec
        self._target_size = int(sample_rate * window_sec) * self._bytes_per_sample
        self._buffer = bytearray()
        self._buffered_sec = 0.0

    def push(self, pcm: bytes) -> tuple[bytes, float] | None:
        self._buffer.extend(pcm)

        samples = len(pcm) // self._bytes_per_sample
        self._buffered_sec += samples / self._sample_rate

        if len(self._buffer) >= self._target_size:
            window = bytes(self._buffer[:self._target_size])

            center_offset = self._buffered_sec - (self._window_sec / 2)

            # overlap 50%
            overlap_bytes = self._target_size // 2
            del self._buffer[:overlap_bytes]
            self._buffered_sec -= self._window_sec / 2

            return window, center_offset

        return None

class AudioOverlapBuffer:

    def __init__(self, max_chunks: int):
        self.buffer = deque(maxlen=max_chunks)

    def push(self, pcm_chunk: bytes):
        self.buffer.append(pcm_chunk)

    def get_overlap(self) -> list[bytes]:
        return list(self.buffer)
