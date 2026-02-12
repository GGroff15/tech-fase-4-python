import logging
from av import AudioFrame

from audio.resampler import AudioResampler16kMono

logger = logging.getLogger("yolo_rest.audio.audio_frame_adapter")


class AudioFrameAdapter:
    
    def __init__(self) -> None:
        self._resampler = AudioResampler16kMono()
        logger.info("AudioFrameAdapter initialized with AudioResampler16kMono")

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
        logger.info(f"PcmChunker initialized: sample_rate={sample_rate}, frame_ms={frame_ms}, chunk_bytes={self.chunk_bytes}")

    def push(self, pcm_bytes: bytes) -> list[bytes]:
        self.buffer.extend(pcm_bytes)

        chunks = []
        while len(self.buffer) >= self.chunk_bytes:
            chunk = self.buffer[:self.chunk_bytes]
            chunks.append(bytes(chunk))
            del self.buffer[:self.chunk_bytes]

        return chunks
