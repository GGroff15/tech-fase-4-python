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

    def __init__(self, sample_rate=16000, frame_ms=20):
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
