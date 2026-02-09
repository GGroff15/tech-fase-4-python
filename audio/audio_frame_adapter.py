import re
from av import AudioFrame
import numpy as np

from audio.resampler import AudioResampler16kMono


class AudioFrameAdapter:
    
    def __init__(self) -> None:
        self._resampler = AudioResampler16kMono()

    def to_pcm16(self, frame: AudioFrame) -> bytes:
        pcm_bytes = bytearray()
        
        for resample in self._resampler.resample(frame):
            array = resample.to_ndarray()
            pcm_bytes.extend(array.tobytes())
        
        return bytes(pcm_bytes)

class PcmChunker:

    def __init__(self, sample_rate=None, frame_ms=None):
        from config import constants
        if sample_rate is None:
            sample_rate = constants.AUDIO_SAMPLE_RATE
        if frame_ms is None:
            frame_ms = constants.AUDIO_FRAME_MS
        self.chunk_bytes = int(sample_rate * frame_ms / 1000) * 2
        self.buffer = bytearray()

    def push(self, pcm_bytes: bytes) -> list[bytes]:
        self.buffer.extend(pcm_bytes)

        chunks = []
        while len(self.buffer) >= self.chunk_bytes:
            chunk = self.buffer[:self.chunk_bytes]
            chunks.append(bytes(chunk))
            del self.buffer[:self.chunk_bytes]

        return chunks
