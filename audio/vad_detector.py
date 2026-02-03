import webrtcvad

class VadDetector:

    def __init__(self, sample_rate=16000, frame_ms=20, aggressiveness=1):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.frame_bytes = int(sample_rate * frame_ms / 1000) * 2

    def is_speech(self, pcm_chunk: bytes) -> bool:
        if len(pcm_chunk) != self.frame_bytes:
            # Invalid chunk size for VAD - skip
            return False
        return self.vad.is_speech(pcm_chunk, self.sample_rate)
