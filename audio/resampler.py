import logging
from av.audio.resampler import AudioResampler
from av import AudioFrame

logger = logging.getLogger("yolo_rest.audio.resampler")


class AudioResampler16kMono:
    def __init__(self):
        self._resampler = AudioResampler(
            format="s16",
            layout="mono",
            rate=16_000,
        )
        logger.info("AudioResampler16kMono initialized: format=s16, layout=mono, rate=16000")

    def resample(self, frame: AudioFrame) -> list[AudioFrame]:
        return self._resampler.resample(frame)