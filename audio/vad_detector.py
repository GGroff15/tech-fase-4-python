import webrtcvad
from config import constants

class VadDetector:

    def __init__(self, sample_rate=None, frame_ms=None, aggressiveness=None):
        if sample_rate is None:
            sample_rate = constants.AUDIO_SAMPLE_RATE
        if frame_ms is None:
            frame_ms = constants.AUDIO_FRAME_MS
        if aggressiveness is None:
            aggressiveness = constants.VAD_AGGRESSIVENESS
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * 2

    def is_speech(self, pcm_chunk: bytes) -> bool:
        if len(pcm_chunk) != self.frame_bytes:
            # Invalid chunk size for VAD - skip
            return False
        return self.vad.is_speech(pcm_chunk, self.sample_rate)
